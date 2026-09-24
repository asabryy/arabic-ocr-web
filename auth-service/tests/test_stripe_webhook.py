"""The webhook is the only path that grants Pro, so it gets the closest scrutiny:
forged payloads must be refused, and replays must not double-apply.
"""
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import settings

URL = "/api/auth/v1/billing/webhook"


def signed(payload: dict, secret="whsec_dummy", timestamp=None):
    """Build a genuine Stripe-Signature header so construct_event accepts the body."""
    body = json.dumps(payload).encode()
    ts = timestamp or int(time.time())
    signature = hmac.new(
        secret.encode(), f"{ts}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return body, {"Stripe-Signature": f"t={ts},v1={signature}"}


def sub_event(
    event_id="evt_1",
    event_type="customer.subscription.updated",
    status="active",
    customer="cus_1",
    sub_id="sub_1",
    metadata=None,
):
    return {
        "id": event_id,
        "type": event_type,
        "data": {
            "object": {
                "id": sub_id,
                "status": status,
                "customer": customer,
                "metadata": metadata or {},
                "items": {"data": [{"price": {"product": "prod_pro"}}]},
            }
        },
    }


def test_unsigned_request_is_rejected(client, stripe_configured, make_user):
    user = make_user(customer_id="cus_1")
    r = client.post(URL, json=sub_event())
    assert r.status_code == 400
    assert user.plan == "free", "an unsigned body must never change a plan"


def test_forged_signature_is_rejected(client, stripe_configured, make_user):
    user = make_user(customer_id="cus_1")
    body, _ = signed(sub_event())
    r = client.post(
        URL, content=body, headers={"Stripe-Signature": "t=1,v1=deadbeef"}
    )
    assert r.status_code == 400
    assert user.plan == "free"


def test_signature_from_wrong_secret_is_rejected(client, stripe_configured, make_user):
    make_user(customer_id="cus_1")
    body, headers = signed(sub_event(), secret="whsec_attacker")
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 400


def test_stale_timestamp_is_rejected(client, stripe_configured, make_user):
    """Replay of a correctly-signed body from long ago (default tolerance is 300s)."""
    make_user(customer_id="cus_1")
    body, headers = signed(sub_event(), timestamp=int(time.time()) - 3600)
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 400


def test_active_subscription_grants_pro(client, stripe_configured, db, make_user):
    user = make_user(customer_id="cus_1")
    body, headers = signed(sub_event(status="active"))
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"
    db.refresh(user)
    assert user.plan == "pro"
    assert user.stripe_subscription_id == "sub_1"


def test_deleted_subscription_revokes_pro(client, stripe_configured, db, make_user):
    user = make_user(plan="pro", customer_id="cus_1", sub_id="sub_1")
    body, headers = signed(
        sub_event(event_type="customer.subscription.deleted", status="canceled")
    )
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 200
    db.refresh(user)
    assert user.plan == "free"


def test_replayed_event_is_applied_once(client, stripe_configured, db, make_user):
    """Stripe re-delivers; the second delivery must be a no-op, not a second apply."""
    user = make_user(customer_id="cus_1")
    body, headers = signed(sub_event(event_id="evt_replay"))
    assert client.post(URL, content=body, headers=headers).json()["status"] == "ok"

    # Manually downgrade, then replay the same event id: it must NOT re-grant.
    user.plan = "free"
    db.commit()
    body2, headers2 = signed(sub_event(event_id="evt_replay"))
    assert client.post(URL, content=body2, headers=headers2).json()["status"] == "duplicate"
    db.refresh(user)
    assert user.plan == "free"


def test_unknown_customer_falls_back_to_metadata(client, stripe_configured, db, make_user):
    """A subscription whose customer id we've never seen still resolves via metadata."""
    user = make_user(customer_id=None)
    body, headers = signed(
        sub_event(customer="cus_unknown", metadata={"user_id": str(user.id)})
    )
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 200
    db.refresh(user)
    assert user.plan == "pro"
    assert user.stripe_customer_id == "cus_unknown", "back-fills the missing customer id"


def test_unresolvable_customer_is_acknowledged(client, stripe_configured):
    """Acknowledge rather than 500 — otherwise Stripe retries a doomed event forever."""
    body, headers = signed(sub_event(customer="cus_nobody"))
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "no_user"


def test_unhandled_event_type_is_ignored(client, stripe_configured, db, make_user):
    user = make_user(customer_id="cus_1")
    body, headers = signed(sub_event(event_type="customer.created"))
    r = client.post(URL, content=body, headers=headers)
    assert r.json()["status"] == "ignored"
    db.refresh(user)
    assert user.plan == "free"


def test_payment_failed_is_noted_but_does_not_downgrade(
    client, stripe_configured, db, make_user
):
    """Smart Retries is still working; the subscription status change drives the plan."""
    user = make_user(plan="pro", customer_id="cus_1", sub_id="sub_1")
    event = {
        "id": "evt_failed",
        "type": "invoice.payment_failed",
        "data": {"object": {"id": "in_1", "customer": "cus_1"}},
    }
    body, headers = signed(event)
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 200
    db.refresh(user)
    assert user.plan == "pro"


def test_webhook_404s_when_secret_unset(client, monkeypatch, make_user):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    body, headers = signed(sub_event())
    assert client.post(URL, content=body, headers=headers).status_code == 404


def test_subscription_state_is_refetched_not_trusted(client, stripe_configured, db, make_user):
    """Stripe can deliver events out of order, so the payload may be stale. The
    handler must act on live state fetched from the API.

    Here the event says `incomplete` (which would revoke) but the live subscription
    is `active` — the user must end up on Pro.
    """
    user = make_user(customer_id="cus_1")

    live = SimpleNamespace(
        to_dict=lambda: {
            "id": "sub_1",
            "status": "active",
            "customer": "cus_1",
            "metadata": {},
            "items": {"data": [{"price": {"product": "prod_pro"}}]},
        }
    )
    fake = SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(retrieve=lambda _id: live)))

    import app.api.api_v1.endpoints.stripe_webhook as hook

    with patch.object(hook, "get_stripe", lambda: fake):
        body, headers = signed(sub_event(status="incomplete"))
        r = client.post(URL, content=body, headers=headers)

    assert r.status_code == 200
    assert r.json()["plan"] == "pro", "live state must win over the stale payload"
    db.refresh(user)
    assert user.plan == "pro"


def test_refetch_failure_falls_back_to_the_payload(client, stripe_configured, db, make_user):
    """A Stripe API blip must not drop the event entirely."""
    user = make_user(customer_id="cus_1")

    def boom(_id):
        raise RuntimeError("stripe unreachable")

    fake = SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(retrieve=boom)))

    import app.api.api_v1.endpoints.stripe_webhook as hook

    with patch.object(hook, "get_stripe", lambda: fake):
        body, headers = signed(sub_event(status="active"))
        r = client.post(URL, content=body, headers=headers)

    assert r.status_code == 200
    db.refresh(user)
    assert user.plan == "pro"


def payment_session_event(event_id="evt_pay", session_id="cs_pay_1"):
    """A completed one-time purchase — what a page pack would produce."""
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "mode": "payment",
                "payment_status": "paid",
                "customer": "cus_1",
                "client_reference_id": "4",
                "metadata": {"user_id": "4"},
            }
        },
    }


def test_payment_mode_is_refused_not_silently_acknowledged(client, stripe_configured, db, make_user):
    """A one-time payment must never be answered 200 while granting nothing.

    Stripe stops retrying on 200, and the event claim would make a replay a no-op —
    so the customer's money would be gone with no recoverable trace.
    """
    make_user(customer_id="cus_1")
    body, headers = signed(payment_session_event())
    r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 500, "must not acknowledge a payment it cannot grant"


def test_refused_payment_event_can_be_retried_later(client, stripe_configured, db, make_user):
    """The claim must roll back, or the retry after shipping packs would be skipped
    as a duplicate and the payment lost anyway."""
    from app.models.billing import StripeEvent

    make_user(customer_id="cus_1")
    body, headers = signed(payment_session_event(event_id="evt_retry"))
    client.post(URL, content=body, headers=headers)

    claimed = db.query(StripeEvent).filter(StripeEvent.event_id == "evt_retry").first()
    assert claimed is None, "event id must not stay claimed after a refusal"


def test_subscription_checkout_is_unaffected(client, stripe_configured, db, make_user):
    """The guard must not disturb the path that actually works today."""
    user = make_user(customer_id="cus_1")
    live = SimpleNamespace(
        to_dict=lambda: {
            "id": "sub_1", "status": "active", "customer": "cus_1",
            "metadata": {}, "items": {"data": [{"price": {"product": "prod_pro"}}]},
        }
    )
    fake = SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(retrieve=lambda _i: live)))
    import app.api.api_v1.endpoints.stripe_webhook as hook

    event = {
        "id": "evt_sub_ok",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_1", "mode": "subscription",
                            "payment_status": "paid", "subscription": "sub_1",
                            "customer": "cus_1", "metadata": {"user_id": str(user.id)}}},
    }
    with patch.object(hook, "get_stripe", lambda: fake):
        body, headers = signed(event)
        r = client.post(URL, content=body, headers=headers)
    assert r.status_code == 200
    db.refresh(user)
    assert user.plan == "pro"
