"""Feedback intake: who may send, what gets attached, and what bots get."""
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.main import app

URL = "/api/auth/v1/feedback"
BODY = {"category": "bug", "message": "Conversion fails on page 3 of my document."}


@pytest.fixture(autouse=True)
def relax_rate_limit(monkeypatch):
    """The limiter is keyed per-IP and every test shares one; reset between tests."""
    from app.core.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def sent():
    with patch("app.api.api_v1.endpoints.feedback.send_feedback_email") as m:
        yield m


def test_anonymous_submission_requires_an_email(client, sent):
    r = client.post(URL, json=BODY)
    assert r.status_code == 422
    sent.assert_not_called()


def test_anonymous_submission_with_email_is_accepted(client, sent):
    r = client.post(URL, json={**BODY, "email": "someone@example.com"})
    assert r.status_code == 202
    kwargs = sent.call_args.kwargs
    assert kwargs["reply_to"] == "someone@example.com"
    assert kwargs["user_id"] is None


def test_signed_in_submission_uses_the_account_email(client, sent, make_user):
    user = make_user(email="real@example.com", plan="pro")
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        # A typed address must not override the authenticated one.
        r = client.post(URL, json={**BODY, "email": "spoofed@example.com", "page": "/convert"})
        assert r.status_code == 202
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_honeypot_is_silently_discarded(client, sent):
    r = client.post(URL, json={**BODY, "email": "bot@example.com", "website": "http://spam"})
    assert r.status_code == 202, "a bot must not be able to tell it was caught"
    sent.assert_not_called()


def test_send_failure_is_reported_as_retryable(client, sent):
    sent.side_effect = RuntimeError("email provider down")
    r = client.post(URL, json={**BODY, "email": "someone@example.com"})
    assert r.status_code == 503


@pytest.mark.parametrize(
    "bad",
    [
        {"category": "nonsense", "message": "x" * 20},
        {"category": "bug", "message": "short"},
        {"category": "bug", "message": "x" * 4001},
    ],
)
def test_invalid_payloads_are_rejected(client, sent, bad):
    assert client.post(URL, json={**bad, "email": "a@example.com"}).status_code == 422
    sent.assert_not_called()


def test_rate_limited_after_the_configured_burst(client, sent, monkeypatch):
    monkeypatch.setattr(settings, "FEEDBACK_RATE_LIMIT", "3/hour")
    payload = {**BODY, "email": "someone@example.com"}
    codes = [client.post(URL, json=payload).status_code for _ in range(5)]
    assert codes[:3] == [202, 202, 202]
    assert 429 in codes, f"expected a 429 after the burst, got {codes}"
