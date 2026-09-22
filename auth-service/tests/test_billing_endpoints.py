"""Checkout and portal routes: gating, not Stripe's behaviour (the SDK is stubbed)."""
from types import SimpleNamespace

import pytest

from app.core import stripe_client
from app.core.dependencies import get_current_user
from app.main import app

CHECKOUT = "/api/auth/v1/billing/checkout-session"
PORTAL = "/api/auth/v1/billing/portal-session"


@pytest.fixture
def as_user(make_user):
    """Authenticate the client as a given user without minting a real JWT."""

    def _as(**kwargs):
        user = make_user(**kwargs)
        app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _as
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def fake_stripe(monkeypatch):
    """Stand in for the Stripe SDK; records the params each call receives."""
    calls = {}

    def customers_create(params, options=None):
        calls["customer"] = (params, options)
        return SimpleNamespace(id="cus_new")

    def checkout_create(params, options=None):
        calls["checkout"] = (params, options)
        return SimpleNamespace(url="https://checkout.stripe.com/c/pay/cs_test_123")

    def portal_create(params, options=None):
        calls["portal"] = (params, options)
        return SimpleNamespace(url="https://billing.stripe.com/p/session/bps_test_123")

    client = SimpleNamespace(
        v1=SimpleNamespace(
            customers=SimpleNamespace(create=customers_create),
            checkout=SimpleNamespace(sessions=SimpleNamespace(create=checkout_create)),
            billing_portal=SimpleNamespace(sessions=SimpleNamespace(create=portal_create)),
        )
    )
    monkeypatch.setattr(stripe_client, "get_stripe", lambda: client)
    # The endpoint module imported the symbol directly.
    import app.api.api_v1.endpoints.billing as billing_ep

    monkeypatch.setattr(billing_ep, "get_stripe", lambda: client)
    return calls


def test_routes_404_when_stripe_unconfigured(client, as_user):
    as_user()
    assert client.post(CHECKOUT).status_code == 404
    assert client.post(PORTAL).status_code == 404


def test_checkout_creates_customer_and_returns_url(
    client, stripe_configured, fake_stripe, as_user, db
):
    user = as_user()
    r = client.post(CHECKOUT)
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://checkout.stripe.com/")

    params, options = fake_stripe["customer"]
    assert params["metadata"]["user_id"] == str(user.id)
    assert options["idempotency_key"] == f"textara-customer-user-{user.id}"

    params, _ = fake_stripe["checkout"]
    assert params["mode"] == "subscription"
    assert params["client_reference_id"] == str(user.id)
    assert params["subscription_data"]["metadata"]["user_id"] == str(user.id)
    assert "payment_method_types" not in params, "must stay dynamic"
    assert "{CHECKOUT_SESSION_ID}" in params["success_url"]

    db.refresh(user)
    assert user.stripe_customer_id == "cus_new"


def test_checkout_reuses_existing_customer(client, stripe_configured, fake_stripe, as_user):
    as_user(customer_id="cus_existing")
    assert client.post(CHECKOUT).status_code == 200
    assert "customer" not in fake_stripe, "must not create a second Stripe customer"
    assert fake_stripe["checkout"][0]["customer"] == "cus_existing"


def test_checkout_rejected_when_already_pro(client, stripe_configured, fake_stripe, as_user):
    as_user(plan="pro", customer_id="cus_1")
    r = client.post(CHECKOUT)
    assert r.status_code == 409


def test_portal_requires_a_billing_account(client, stripe_configured, fake_stripe, as_user):
    as_user(customer_id=None)
    assert client.post(PORTAL).status_code == 404


def test_portal_returns_url(client, stripe_configured, fake_stripe, as_user):
    as_user(plan="pro", customer_id="cus_1")
    r = client.post(PORTAL)
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://billing.stripe.com/")
    assert fake_stripe["portal"][0]["customer"] == "cus_1"
