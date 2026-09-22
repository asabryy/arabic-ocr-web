"""Email sending: outcomes are counted, and a missing key never breaks signup."""
from unittest.mock import Mock, patch

import pytest
import requests
from prometheus_client import REGISTRY

from app.core import email
from app.core.config import settings


def count(kind, outcome):
    return REGISTRY.get_sample_value(
        "textara_emails_total", {"kind": kind, "outcome": outcome}
    ) or 0.0


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "https://textara.app")


@pytest.fixture
def post():
    with patch("app.core.email.requests.post") as m:
        m.return_value = Mock(status_code=200, json=lambda: {"id": "abc"}, text="")
        yield m


def test_verification_email_carries_the_token_link(configured, post):
    before = count("verification", "sent")
    email.send_verification_email("a@example.com", "tok123")
    body = post.call_args.kwargs["json"]
    assert body["to"] == ["a@example.com"]
    assert "https://textara.app/verify-email?token=tok123" in body["html"]
    assert count("verification", "sent") == before + 1


def test_password_reset_email_carries_the_token_link(configured, post):
    email.send_password_reset_email("a@example.com", "rst456")
    assert "https://textara.app/reset-password?token=rst456" in post.call_args.kwargs["json"]["html"]


def test_feedback_email_sets_reply_to_the_sender(configured, post):
    email.send_feedback_email(
        category="bug", message="it broke", reply_to="user@example.com",
        user_id=7, plan="pro", page="/convert",
    )
    body = post.call_args.kwargs["json"]
    assert body["reply_to"] == "user@example.com"
    assert body["to"] == [settings.SUPPORT_EMAIL]
    assert "it broke" in body["html"]


def test_user_content_is_escaped(configured, post):
    """A feedback message is attacker-controlled and lands in an HTML email."""
    email.send_feedback_email(
        category="bug", message="<script>alert(1)</script>", reply_to="a@example.com",
    )
    html = post.call_args.kwargs["json"]["html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_missing_key_is_skipped_not_raised(monkeypatch, post):
    """Local dev and CI have no credentials; signup must still work."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    before = count("verification", "skipped")
    email.send_verification_email("a@example.com", "tok")
    post.assert_not_called()
    assert count("verification", "skipped") == before + 1


def test_rejected_send_counts_a_failure_and_raises(configured, post):
    """The SendGrid outage was invisible because nothing counted failures."""
    post.return_value = Mock(
        status_code=403,
        text='{"message":"The textara.app domain is not verified"}',
        raise_for_status=Mock(side_effect=requests.HTTPError("403")),
        json=lambda: {},
    )
    before = count("verification", "failed")
    with pytest.raises(requests.HTTPError):
        email.send_verification_email("a@example.com", "tok")
    assert count("verification", "failed") == before + 1


def test_network_error_counts_a_failure_and_raises(configured, post):
    post.side_effect = requests.ConnectionError("no route")
    before = count("password_reset", "failed")
    with pytest.raises(requests.ConnectionError):
        email.send_password_reset_email("a@example.com", "tok")
    assert count("password_reset", "failed") == before + 1


def test_non_json_success_body_still_counts_as_sent(configured, post):
    """A 2xx with a surprising body must not turn a delivered message into a 503."""
    post.return_value = Mock(
        status_code=202,
        json=Mock(side_effect=ValueError("no json")),
        text="",
    )
    before = count("verification", "sent")
    email.send_verification_email("a@example.com", "tok")  # must not raise
    assert count("verification", "sent") == before + 1


def test_links_are_not_logged_by_default(monkeypatch, post, caplog):
    """A reset link is a live credential; logs outlive it and are widely readable."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "EMAIL_ECHO_LINKS", False)
    with caplog.at_level("DEBUG"):
        email.send_password_reset_email("a@example.com", "tok789")
    assert "tok789" not in caplog.text


def test_links_are_echoed_only_when_explicitly_enabled(monkeypatch, post, caplog):
    """Opt-in escape hatch so local dev without credentials stays usable."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "EMAIL_ECHO_LINKS", True)
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")
    with caplog.at_level("INFO"):
        email.send_password_reset_email("a@example.com", "tok789")
    assert "http://localhost:3000/reset-password?token=tok789" in caplog.text
