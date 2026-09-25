"""Which subscription states grant Pro, and the event-claim guard."""
import pytest

from app.core.config import settings
from app.services import billing


def sub(status="active", product="prod_pro", sub_id="sub_1", customer="cus_1"):
    return {
        "id": sub_id,
        "status": status,
        "customer": customer,
        "items": {"data": [{"price": {"product": product}}]},
    }


@pytest.mark.parametrize("status", ["active", "trialing", "past_due"])
def test_live_statuses_grant_pro(status):
    assert billing.plan_for_subscription(sub(status=status)) == "pro"


@pytest.mark.parametrize(
    "status", ["canceled", "unpaid", "incomplete", "incomplete_expired", "paused"]
)
def test_dead_statuses_revoke_pro(status):
    assert billing.plan_for_subscription(sub(status=status)) == "free"


def test_past_due_keeps_access_during_smart_retries():
    """A failed renewal must not cut off access while Stripe is still retrying."""
    assert billing.plan_for_subscription(sub(status="past_due")) == "pro"


def test_product_gate_rejects_other_products(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_PRODUCT_PRO", "prod_pro")
    assert billing.plan_for_subscription(sub(product="prod_pro")) == "pro"
    assert billing.plan_for_subscription(sub(product="prod_something_else")) == "free"


def test_product_gate_open_when_unset(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_PRODUCT_PRO", "")
    assert billing.plan_for_subscription(sub(product="prod_anything")) == "pro"


def test_expanded_product_object_is_understood(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_PRODUCT_PRO", "prod_pro")
    payload = sub()
    payload["items"]["data"][0]["price"]["product"] = {"id": "prod_pro"}
    assert billing.plan_for_subscription(payload) == "pro"


def test_apply_subscription_grants_and_records(db, make_user):
    user = make_user()
    plan = billing.apply_subscription(db, user, sub(status="active"))
    db.commit()
    assert plan == "pro"
    assert user.plan == "pro"
    assert user.subscription_status == "active"
    assert user.stripe_subscription_id == "sub_1"


def test_apply_subscription_revokes_and_clears_pointer(db, make_user):
    user = make_user(plan="pro", customer_id="cus_1", sub_id="sub_1")
    plan = billing.apply_subscription(db, user, sub(status="canceled"))
    db.commit()
    assert plan == "free"
    assert user.plan == "free"
    assert user.stripe_subscription_id is None
    # Customer id survives so a re-subscribe reuses their billing history.
    assert user.stripe_customer_id == "cus_1"


def test_claim_event_is_single_use(db):
    assert billing.claim_event(db, "evt_1", "customer.subscription.updated") is True
    db.commit()
    assert billing.claim_event(db, "evt_1", "customer.subscription.updated") is False


def test_stale_revoking_event_for_an_old_subscription_is_ignored(db, make_user):
    """A customer who re-subscribed after a failed card has two subscriptions.
    The old one's eventual cancellation must not revoke the new one's access."""
    user = make_user(plan="pro", customer_id="cus_1", sub_id="sub_new")
    plan = billing.apply_subscription(db, user, sub(status="canceled", sub_id="sub_old"))
    db.commit()
    assert plan == "pro", "the live subscription still entitles them"
    assert user.plan == "pro"
    assert user.stripe_subscription_id == "sub_new", "pointer must not move to the dead sub"


def test_revoking_event_for_the_current_subscription_still_applies(db, make_user):
    user = make_user(plan="pro", customer_id="cus_1", sub_id="sub_1")
    plan = billing.apply_subscription(db, user, sub(status="canceled", sub_id="sub_1"))
    db.commit()
    assert plan == "free"
    assert user.stripe_subscription_id is None


def test_upgrade_still_applies_when_no_subscription_is_recorded(db, make_user):
    """First purchase: nothing to compare against, so the guard must not block it."""
    user = make_user(customer_id="cus_1", sub_id=None)
    assert billing.apply_subscription(db, user, sub(status="active", sub_id="sub_1")) == "pro"


# ── the comped tier ──────────────────────────────────────────────────────────

def test_unlimited_is_a_real_tier_not_a_silent_downgrade():
    """quota.limits_for falls through to FREE for any plan it does not know, so a
    tier that exists in the schema but not in that function would hand a comped
    account *fewer* pages than Pro. Pin the contract from this side."""
    from app.schemas.user import PlanUpdate

    assert PlanUpdate(plan="unlimited").plan == "unlimited"
    assert PlanUpdate(plan="pro").notify is False  # notification is opt-in

    import pydantic

    with pytest.raises(pydantic.ValidationError):
        PlanUpdate(plan="platinum")
