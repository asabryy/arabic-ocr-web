"""The webhook is the only path that grants Pro, so it gets the closest scrutiny:
forged payloads must be refused, and replays must not double-apply.
"""
import hashlib
import hmac
import json
import time

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
