"""Worker consumer: redelivery guard and heartbeat-safe ack."""

import json
import threading

from app.worker import consumer


def test_redelivered_terminal_task_is_skipped(storage, monkeypatch):
    storage.set_status("42", "a.pdf", "failed")
    called = []
    monkeypatch.setattr(consumer, "_call_gemini", lambda *a, **k: called.append(1) or b"PK")
    monkeypatch.setattr(consumer, "_refund_pages", lambda *a, **k: called.append("refund"))

    consumer.process_task({"file_id": "a.pdf", "user_id": "42", "pages": 3}, redelivered=True)

    assert called == []
    assert storage.get_status("42", "a.pdf") == "failed"


def test_redelivered_processing_task_is_retried(storage, monkeypatch):
    """A crash mid-task leaves 'processing'; that redelivery must run."""
    storage.set_status("42", "a.pdf", "processing")
    monkeypatch.setattr(consumer, "OCR_BACKEND", "gemini")
    monkeypatch.setattr(consumer, "_call_gemini", lambda *a, **k: b"PK\x03\x04docx")
    import io

    storage.save_file("42", "a.pdf", io.BytesIO(b"%PDF-1.4 fake"))

    consumer.process_task({"file_id": "a.pdf", "user_id": "42", "pages": 1}, redelivered=True)

    assert storage.get_status("42", "a.pdf") == "done"


def test_callback_acks_via_threadsafe_callback_after_work(monkeypatch):
    """The AMQP callback must return immediately and ack from the worker thread."""
    done = threading.Event()
    acked = []

    class FakeConn:
        def add_callback_threadsafe(self, fn):
            fn()
            done.set()

    class FakeCh:
        def basic_ack(self, delivery_tag):
            acked.append(delivery_tag)

    class Method:
        delivery_tag = 7
        redelivered = False

    seen = {}

    def fake_process(task, redelivered=False):
        seen["task"] = task
        seen["thread"] = threading.current_thread().name

    monkeypatch.setattr(consumer, "process_task", fake_process)
    cb = consumer._make_callback(FakeConn())
    cb(FakeCh(), Method(), None, json.dumps({"file_id": "x", "user_id": "1"}).encode())

    assert done.wait(5)
    assert acked == [7]
    assert seen["task"]["file_id"] == "x"
    assert seen["thread"] == "ocr-task"
