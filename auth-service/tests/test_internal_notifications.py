"""The worker's conversion-finished callback: who may call it, and who it can mail.

The security property worth pinning: the payload carries a user id, never an address,
so this endpoint cannot be used to mail an arbitrary inbox even by someone holding the
shared key. And it does not exist at all until INTERNAL_API_KEY is configured.
"""
from unittest.mock import patch

import pytest

from app.api.api_v1.endpoints.internal import INTERNAL_KEY_ENV

URL = "/api/auth/v1/internal/notifications/conversion"
KEY = "internal-test-key"
BODY = {
    "user_id": 1,
    "filename": "thesis.pdf",
    "outcome": "done",
    "pages": 40,
    "duration_seconds": 412.0,
}


@pytest.fixture(autouse=True)
def relax_rate_limit():
    from app.core.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv(INTERNAL_KEY_ENV, KEY)


@pytest.fixture
def sent():
    with patch("app.api.api_v1.endpoints.internal.send_conversion_complete_email") as m:
        yield m


# ── access control ────────────────────────────────────────────────────────────

def test_route_does_not_exist_until_a_key_is_configured(client, sent, monkeypatch):
    """An unconfigured or public-facing deployment exposes nothing at all."""
    monkeypatch.delenv(INTERNAL_KEY_ENV, raising=False)
    assert client.post(URL, json=BODY).status_code == 404
    assert client.post(URL, json=BODY, headers={"X-Internal-Key": KEY}).status_code == 404
    sent.assert_not_called()


def test_missing_or_wrong_key_is_rejected(client, configured, sent):
    assert client.post(URL, json=BODY).status_code == 403
    assert client.post(URL, json=BODY, headers={"X-Internal-Key": "guess"}).status_code == 403
    sent.assert_not_called()


def test_it_is_not_in_the_public_schema(client, configured):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any("internal" in p for p in paths)


def test_the_caller_cannot_choose_the_recipient(client, configured, sent, make_user):
    """The anti-open-relay property: an attacker-supplied address is ignored."""
    user = make_user(email="owner@example.com")
    r = client.post(
        URL,
        json={**BODY, "user_id": user.id, "to": "victim@example.com",
              "email": "victim@example.com"},
        headers={"X-Internal-Key": KEY},
    )
    assert r.status_code == 202
    assert sent.call_args.args[0] == "owner@example.com"


# ── behaviour ─────────────────────────────────────────────────────────────────

def test_accepted_call_mails_the_account_owner(client, configured, sent, make_user):
    user = make_user(email="real@example.com")
    r = client.post(
        URL, json={**BODY, "user_id": user.id}, headers={"X-Internal-Key": KEY}
    )
    assert r.status_code == 202
    assert sent.call_args.args[0] == "real@example.com"
    kwargs = sent.call_args.kwargs
    assert kwargs["filename"] == "thesis.pdf"
    assert kwargs["outcome"] == "done"
    assert kwargs["pages"] == 40


def test_failure_outcome_carries_its_reason(client, configured, sent, make_user):
    user = make_user(email="real@example.com")
    r = client.post(
        URL,
        json={**BODY, "user_id": user.id, "outcome": "failed", "reason": "no_text"},
        headers={"X-Internal-Key": KEY},
    )
    assert r.status_code == 202
    assert sent.call_args.kwargs["reason"] == "no_text"


def test_unknown_user_is_accepted_and_skipped(client, configured, sent):
    """An account deleted mid-conversion is a race, not an outage — don't alarm."""
    r = client.post(
        URL, json={**BODY, "user_id": 999999}, headers={"X-Internal-Key": KEY}
    )
    assert r.status_code == 202
    assert r.json()["status"] == "skipped"
    sent.assert_not_called()


def test_a_bad_outcome_value_is_rejected(client, configured, sent, make_user):
    user = make_user()
    r = client.post(
        URL,
        json={**BODY, "user_id": user.id, "outcome": "whatever"},
        headers={"X-Internal-Key": KEY},
    )
    assert r.status_code == 422
    sent.assert_not_called()


def test_a_send_failure_is_surfaced_to_the_worker(client, configured, sent, make_user):
    user = make_user()
    sent.side_effect = RuntimeError("resend down")
    r = client.post(
        URL, json={**BODY, "user_id": user.id}, headers={"X-Internal-Key": KEY}
    )
    assert r.status_code == 503
