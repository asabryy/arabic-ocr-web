"""The worker's choice between the two conversion paths.

Most uploads already contain their text, and reading it costs nothing; only scans,
batched tashkeel and broken font maps need the vision model. These tests pin the
routing itself, and — more importantly — the fallback: a document triage thought
was clean but which the digital path could not read must still reach the user,
converted by Gemini, rather than failing.
"""

import io

import pytest
from docx import Document
from prometheus_client import REGISTRY

from app.core.config import settings
from app.ocr import triage
from app.worker import consumer

ARABIC = "هذا نص عربي حقيقي يكفي لتجاوز حد الحروف المرئية"


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def make_docx(text: str = ARABIC) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def route(decision_route, reason=triage.REASON_CLEAN):
    return triage.Triage(decision_route, reason, pages=1, text_pages=1)


@pytest.fixture
def run(storage, monkeypatch):
    """Run one task, recording which converters were called."""
    calls: list[str] = []
    refunds: list[tuple] = []
    monkeypatch.setattr(consumer, "OCR_BACKEND", "gemini")
    monkeypatch.setattr(consumer, "_refund_pages", lambda *a, **k: refunds.append((a, k)))

    def _run(*, decision, digital=None, gemini=None, task=None,
             user_id="42", file_id="a.pdf", pages=3):
        monkeypatch.setattr(triage, "classify", lambda *a, **k: decision)

        def _digital(*a, **k):
            calls.append("digital")
            if isinstance(digital, Exception):
                raise digital
            return digital

        def _gemini(*a, **k):
            calls.append("gemini")
            if isinstance(gemini, Exception):
                raise gemini
            return gemini if gemini is not None else make_docx()

        monkeypatch.setattr(consumer, "_call_digital", _digital)
        monkeypatch.setattr(consumer, "_call_gemini", _gemini)
        storage.save_file(user_id, file_id, io.BytesIO(b"%PDF-1.4 fake"))
        payload = {"file_id": file_id, "user_id": user_id, "pages": pages, "mode": "ocr"}
        payload.update(task or {})
        consumer.process_task(payload)
        return storage.get_status(user_id, file_id)

    _run.calls = calls
    _run.refunds = refunds
    return _run


# ── Routing ──────────────────────────────────────────────────────────────────


def test_clean_document_is_converted_without_calling_gemini(run):
    assert run(decision=route(triage.ROUTE_DIGITAL), digital=make_docx()) == "done"
    assert run.calls == ["digital"], "a clean document should never reach the model"


def test_diverted_document_goes_straight_to_gemini(run):
    status = run(
        decision=route(triage.ROUTE_GEMINI, triage.REASON_BATCHED_TASHKEEL),
        gemini=make_docx(),
    )
    assert status == "done"
    assert run.calls == ["gemini"], "triage said gemini; digital must not be attempted"


def test_route_is_counted_with_its_reason(run):
    before = sample("ocr_route_total", route="digital", reason="clean")
    run(decision=route(triage.ROUTE_DIGITAL), digital=make_docx())
    assert sample("ocr_route_total", route="digital", reason="clean") == before + 1


# ── Fallback ─────────────────────────────────────────────────────────────────


def test_digital_failure_falls_back_to_gemini(run):
    """A crash in extraction is Gemini's cue, not the user's problem."""
    status = run(
        decision=route(triage.ROUTE_DIGITAL),
        digital=RuntimeError("glyph table on fire"),
        gemini=make_docx(),
    )
    assert status == "done"
    assert run.calls == ["digital", "gemini"]
    assert not run.refunds, "a conversion that succeeded must not refund"


def test_blank_digital_output_falls_back_rather_than_failing(run):
    """The digital path can produce a valid, empty document — a text layer that
    extracted to nothing. That is a fallback trigger, not a failure."""
    status = run(
        decision=route(triage.ROUTE_DIGITAL),
        digital=make_docx(""),
        gemini=make_docx(),
    )
    assert status == "done"
    assert run.calls == ["digital", "gemini"]


def test_fallbacks_are_counted_separately_from_routes(run):
    """A climbing fallback rate means triage is wrong about which documents are
    clean — a different problem from users uploading more scans."""
    before = sample("ocr_fallbacks_total", reason="error")
    run(decision=route(triage.ROUTE_DIGITAL),
        digital=RuntimeError("boom"), gemini=make_docx())
    assert sample("ocr_fallbacks_total", reason="error") == before + 1


def test_failure_after_fallback_fails_the_task_and_refunds(run):
    """Only when BOTH paths fail does the user lose the conversion."""
    status = run(
        decision=route(triage.ROUTE_DIGITAL),
        digital=RuntimeError("digital boom"),
        gemini=RuntimeError("gemini boom"),
    )
    assert status == "failed"
    assert run.calls == ["digital", "gemini"]
    assert run.refunds, "a failed conversion must give the pages back"


def test_blank_output_from_both_paths_still_fails(run):
    status = run(
        decision=route(triage.ROUTE_DIGITAL),
        digital=make_docx(""),
        gemini=make_docx(""),
    )
    assert status == "failed"
    assert run.refunds


# ── The style option ─────────────────────────────────────────────────────────


def test_style_travels_from_the_task_to_the_extractor(storage, monkeypatch):
    seen = {}
    monkeypatch.setattr(consumer, "OCR_BACKEND", "gemini")
    monkeypatch.setattr(triage, "classify", lambda *a, **k: route(triage.ROUTE_DIGITAL))

    def _digital(pdf_bytes, max_pages=None, style="source", mode="ocr"):
        seen["style"] = style
        return make_docx()

    monkeypatch.setattr(consumer, "_call_digital", _digital)
    storage.save_file("42", "a.pdf", io.BytesIO(b"%PDF-1.4 fake"))
    consumer.process_task(
        {"file_id": "a.pdf", "user_id": "42", "pages": 1, "mode": "ocr", "style": "uniform"}
    )
    assert seen["style"] == "uniform"


def test_task_without_a_style_uses_the_configured_default(storage, monkeypatch):
    """Messages queued by an older API image carry no style field."""
    seen = {}
    monkeypatch.setattr(consumer, "OCR_BACKEND", "gemini")
    monkeypatch.setattr(triage, "classify", lambda *a, **k: route(triage.ROUTE_DIGITAL))
    monkeypatch.setattr(
        consumer, "_call_digital",
        lambda pdf, max_pages=None, style="source", mode="ocr": (
            seen.update(style=style) or make_docx()
        ),
    )
    storage.save_file("42", "a.pdf", io.BytesIO(b"%PDF-1.4 fake"))
    consumer.process_task({"file_id": "a.pdf", "user_id": "42", "pages": 1, "mode": "ocr"})
    assert seen["style"] == settings.DIGITAL_DEFAULT_STYLE


# ── Backend seam ─────────────────────────────────────────────────────────────


def test_http_backend_bypasses_routing_entirely(storage, monkeypatch):
    """The local-dev OCR server is a whole-pipeline replacement; triage does not
    apply to it."""
    calls = []
    monkeypatch.setattr(consumer, "OCR_BACKEND", "http")
    monkeypatch.setattr(consumer, "_call_http", lambda *a, **k: (calls.append("http") or make_docx()))
    monkeypatch.setattr(triage, "classify", lambda *a, **k: pytest.fail("triage ran for http"))
    storage.save_file("42", "a.pdf", io.BytesIO(b"%PDF-1.4 fake"))
    consumer.process_task({"file_id": "a.pdf", "user_id": "42", "pages": 1, "mode": "ocr"})
    assert calls == ["http"]
