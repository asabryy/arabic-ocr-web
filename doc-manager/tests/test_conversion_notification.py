"""The worker tells auth-service a conversion finished, and never trips over it.

Conversions run for minutes and the frontend only polls while the Convert page is
mounted, so a user who closes the tab was never told anything. The worker posts a
user id and an outcome to an internal auth-service route; everything about that call
is best-effort, because a conversion that succeeded must stay succeeded.
"""

import io

import pytest
from prometheus_client import REGISTRY

from app.core.config import settings
from app.worker import consumer
from tests.test_blank_output import make_docx

ARABIC = "هذا نص عربي حقيقي من الصفحة الممسوحة"
GOOD_DOCX = make_docx([ARABIC, ARABIC])


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.fixture
def posts(monkeypatch):
    """Capture the notification POST instead of reaching auth-service."""
    calls: list[dict] = []

    class Resp:
        status_code = 202

        def raise_for_status(self):
            pass

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return Resp()

    monkeypatch.setattr(consumer.requests, "post", fake_post)
    return calls


@pytest.fixture
def notify_on(monkeypatch):
    monkeypatch.setattr(settings, "NOTIFY_URL", "http://auth/api/auth/v1/internal/notifications/conversion")
    monkeypatch.setattr(settings, "NOTIFY_API_KEY", "shared-secret")
    monkeypatch.setattr(settings, "NOTIFY_MIN_SECONDS", 0.0)


@pytest.fixture
def run(storage, monkeypatch):
    monkeypatch.setattr(consumer, "OCR_BACKEND", "gemini")
    monkeypatch.setattr(consumer, "_refund_pages", lambda *a, **k: None)

    def _run(docx_bytes=GOOD_DOCX, *, user_id="42", file_id="a.pdf", pages=4):
        # A callable stands in for the backend itself, so a test can make it blow up.
        backend = docx_bytes if callable(docx_bytes) else (lambda *a, **k: docx_bytes)
        monkeypatch.setattr(consumer, "_call_gemini", backend)
        storage.save_file(user_id, file_id, io.BytesIO(b"%PDF-1.4 fake"))
        consumer.process_task(
            {"file_id": file_id, "user_id": user_id, "pages": pages, "mode": "ocr"}
        )
        return storage.get_status(user_id, file_id)

    return _run


# ── the happy path ────────────────────────────────────────────────────────────

def test_finished_conversion_is_notified(run, posts, notify_on):
    sent0 = sample("textara_conversion_notifications_total", outcome="sent")

    assert run() == "done"

    assert len(posts) == 1
    body = posts[0]["json"]
    assert body["user_id"] == 42 and isinstance(body["user_id"], int)
    assert body["filename"] == "a.pdf"
    assert body["outcome"] == "done"
    assert body["pages"] == 4
    assert body["duration_seconds"] >= 0
    # Authenticated, and bounded so a hung auth-service cannot stall the queue.
    assert posts[0]["headers"]["X-Internal-Key"] == "shared-secret"
    assert posts[0]["timeout"] == settings.NOTIFY_TIMEOUT_S
    assert sample("textara_conversion_notifications_total", outcome="sent") == sent0 + 1


def test_blank_document_notifies_the_failure_with_its_reason(run, posts, notify_on):
    assert run(make_docx(["", ""])) == "failed"
    assert posts[0]["json"]["outcome"] == "failed"
    assert posts[0]["json"]["reason"] == "no_text"


def test_crashed_conversion_notifies_the_failure(run, posts, notify_on):
    def boom(*a, **k):
        raise RuntimeError("gemini down")

    assert run(boom) == "failed"
    assert posts[0]["json"]["outcome"] == "failed"
    assert posts[0]["json"]["reason"] == "error"


# ── the negative cases ────────────────────────────────────────────────────────

def test_anonymous_trial_is_never_notified(run, posts, notify_on):
    """A trial owner has no account and no address."""
    skipped0 = sample("textara_conversion_notifications_total", outcome="skipped")
    assert run(user_id="trial/abc123", pages=None) == "done"
    assert posts == []
    assert sample("textara_conversion_notifications_total", outcome="skipped") == skipped0 + 1


def test_short_job_is_not_notified(run, posts, notify_on, monkeypatch):
    """Five quick documents in one session must not mean five emails.

    Under the threshold the Convert page is almost certainly still open and has
    already shown the result.
    """
    monkeypatch.setattr(settings, "NOTIFY_MIN_SECONDS", 600.0)
    assert run() == "done"
    assert posts == []


def test_nothing_is_sent_when_unconfigured(run, posts, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFY_URL", "")
    monkeypatch.setattr(settings, "NOTIFY_API_KEY", "")
    monkeypatch.setattr(settings, "NOTIFY_MIN_SECONDS", 0.0)
    assert run() == "done"
    assert posts == []


def test_notification_failure_does_not_fail_the_conversion(run, notify_on, monkeypatch, storage):
    """The whole point: a broken notifier must not un-succeed a conversion."""
    def boom(*a, **k):
        raise OSError("auth-service unreachable")

    monkeypatch.setattr(consumer.requests, "post", boom)
    failed0 = sample("textara_conversion_notifications_total", outcome="failed")
    ok0 = sample("ocr_requests_total", status="success", mode="ocr")

    assert run() == "done"

    assert storage.file_exists("42", "a.docx")
    assert sample("ocr_requests_total", status="success", mode="ocr") == ok0 + 1
    assert sample("textara_conversion_notifications_total", outcome="failed") == failed0 + 1


def test_rejected_notification_does_not_fail_the_conversion(run, notify_on, monkeypatch):
    """A 500 from auth-service is counted, not propagated."""
    class Resp:
        status_code = 500

        def raise_for_status(self):
            raise RuntimeError("500 Server Error")

    monkeypatch.setattr(consumer.requests, "post", lambda *a, **k: Resp())
    failed0 = sample("textara_conversion_notifications_total", outcome="failed")
    assert run() == "done"
    assert sample("textara_conversion_notifications_total", outcome="failed") == failed0 + 1
