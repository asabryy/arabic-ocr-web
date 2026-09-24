"""The conversion-finished email: what it says, where it links, and that it is counted."""
from unittest.mock import Mock, patch

import pytest
from prometheus_client import REGISTRY

from app.core import email
from app.core.config import settings


def count(outcome, kind="conversion"):
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


def test_the_kind_exists_at_zero_before_anything_is_sent():
    """A counter child that does not exist makes a total outage read as "No data"."""
    for outcome in ("sent", "failed", "skipped"):
        assert REGISTRY.get_sample_value(
            "textara_emails_total", {"kind": "conversion", "outcome": outcome}
        ) is not None


def test_success_email_names_the_file_and_links_to_it(configured, post):
    before = count("sent")
    email.send_conversion_complete_email(
        "a@example.com", filename="thesis.pdf", outcome="done",
        pages=40, duration_seconds=412,
    )
    body = post.call_args.kwargs["json"]
    assert body["to"] == ["a@example.com"]
    assert "thesis.pdf" in body["subject"]
    assert "thesis.pdf" in body["html"]
    assert "40 pages" in body["html"]
    assert "6 minutes 52 seconds" in body["html"]
    assert "https://textara.app/dashboard" in body["html"]
    assert count("sent") == before + 1


def test_failure_email_explains_a_blank_scan_and_the_refund(configured, post):
    email.send_conversion_complete_email(
        "a@example.com", filename="scan.pdf", outcome="failed",
        pages=3, duration_seconds=180, reason="no_text",
    )
    body = post.call_args.kwargs["json"]
    assert "couldn't convert" in body["subject"]
    assert "readable text" in body["html"]
    assert "not counted against your daily allowance" in body["html"]


def test_generic_failure_does_not_blame_the_scan(configured, post):
    email.send_conversion_complete_email(
        "a@example.com", filename="scan.pdf", outcome="failed", reason="error",
    )
    html_body = post.call_args.kwargs["json"]["html"]
    assert "readable text" not in html_body
    assert "went wrong on our side" in html_body


def test_a_hostile_filename_cannot_inject_markup(configured, post):
    email.send_conversion_complete_email(
        "a@example.com", filename='<img src=x onerror=alert(1)>.pdf', outcome="done",
    )
    html_body = post.call_args.kwargs["json"]["html"]
    assert "<img" not in html_body
    assert "&lt;img" in html_body


def test_a_very_long_filename_is_truncated(configured, post):
    email.send_conversion_complete_email(
        "a@example.com", filename="x" * 300 + ".pdf", outcome="done",
    )
    assert len(post.call_args.kwargs["json"]["subject"]) < 120


def test_no_remote_images_and_no_external_css(configured, post):
    """Same house style as the other three: remote content reads as phishing."""
    email.send_conversion_complete_email("a@example.com", filename="a.pdf", outcome="done")
    html_body = post.call_args.kwargs["json"]["html"]
    assert "<img" not in html_body
    assert "<link" not in html_body and "@import" not in html_body


def test_missing_api_key_is_a_counted_skip_not_a_crash(monkeypatch, post):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    before = count("skipped")
    email.send_conversion_complete_email("a@example.com", filename="a.pdf", outcome="done")
    post.assert_not_called()
    assert count("skipped") == before + 1


@pytest.mark.parametrize(
    "seconds,expected",
    [(None, ""), (0, ""), (45, "45 seconds"), (60, "1 minute"), (90, "1 minute 30 seconds"),
     (240, "4 minutes")],
)
def test_duration_wording(seconds, expected):
    assert email._human_duration(seconds) == expected
