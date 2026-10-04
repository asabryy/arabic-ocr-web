"""Route selection.

Triage decides, before either path runs, whether a document can be read from its
text layer. Getting it wrong is expensive in both directions: a false "digital"
hands the user wrong text, a false "gemini" pays $0.0036 a page for nothing.

The thresholds here were measured over 293 real documents (11,336 pages).
"""

import fitz
import pytest

from app.core.config import settings
from app.ocr import triage


def pdf_with_text(pages: int = 1, text: str = "نص عربي طويل بما يكفي ليعد صفحة نصية") -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        # Repeated so the page clears the 50-character floor.
        for i in range(4):
            page.insert_text((72, 72 + i * 20), text)
    data = doc.tobytes()
    doc.close()
    return data


def pdf_of_images(pages: int = 1) -> bytes:
    """A scan: a full-page raster and no text layer."""
    doc = fitz.open()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 600, 850))
    pix.set_rect(pix.irect, (255, 255, 255))
    for _ in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_image(page.rect, pixmap=pix)
    data = doc.tobytes()
    doc.close()
    return data


# ── The happy path ───────────────────────────────────────────────────────────


def test_text_bearing_pdf_goes_digital():
    decision = triage.classify(pdf_with_text(3))
    assert decision.route == triage.ROUTE_DIGITAL
    assert decision.reason == triage.REASON_CLEAN
    assert decision.is_digital


def test_scan_goes_to_gemini():
    decision = triage.classify(pdf_of_images(2))
    assert decision.route == triage.ROUTE_GEMINI
    assert decision.reason == triage.REASON_NO_TEXT_LAYER


def test_mostly_scanned_document_goes_to_gemini():
    """Below the text-page ratio the document is a scan with a few typed pages,
    not a digital document with a few images."""
    doc = fitz.open(stream=pdf_of_images(4), filetype="pdf")
    text = fitz.open(stream=pdf_with_text(1), filetype="pdf")
    doc.insert_pdf(text)
    data = doc.tobytes()
    doc.close()
    text.close()
    assert triage.classify(data).route == triage.ROUTE_GEMINI


# ── Failure signals ──────────────────────────────────────────────────────────


def test_batched_tashkeel_goes_to_gemini(monkeypatch):
    """Marks sharing coordinates mean the typesetter batched them at shared pen
    positions; which letter each belongs to is simply not in the file."""
    monkeypatch.setattr(
        triage, "_mark_counts", lambda page: (100, 40)   # 40% batched
    )
    decision = triage.classify(pdf_with_text(2))
    assert decision.route == triage.ROUTE_GEMINI
    assert decision.reason == triage.REASON_BATCHED_TASHKEEL
    assert decision.mark_batching == pytest.approx(0.4, abs=0.01)


def test_a_few_colliding_marks_are_not_enough_to_divert(monkeypatch):
    """The floor that stops the detector firing on noise.

    Without it, a page carrying two marks that happen to collide scores 100%. On
    the real corpus that difference was 42% of documents diverted versus 23%.
    """
    monkeypatch.setattr(triage, "_mark_counts", lambda page: (4, 2))  # 50%, but tiny
    decision = triage.classify(pdf_with_text(2))
    assert decision.route == triage.ROUTE_DIGITAL
    assert decision.mark_batching == 0.0


def test_batching_is_pooled_across_pages_not_maxed(monkeypatch):
    """One bad page must not condemn a long clean document.

    Page 1 is fully batched and the remaining nine are clean: pooled that is 10
    duplicates in 100 marks, under the threshold. Taking the worst page would
    divert the document.
    """
    pages = iter([(10, 10)] + [(10, 0)] * 9)
    monkeypatch.setattr(triage, "_mark_counts", lambda page: next(pages))
    decision = triage.classify(pdf_with_text(10))
    assert decision.route == triage.ROUTE_DIGITAL
    assert decision.mark_batching == pytest.approx(0.1, abs=0.01)


def test_broken_tounicode_goes_to_gemini(monkeypatch):
    monkeypatch.setattr(triage, "_suspect_chars", lambda page: 3)
    decision = triage.classify(pdf_with_text(1))
    assert decision.route == triage.ROUTE_GEMINI
    assert decision.reason == triage.REASON_BROKEN_TOUNICODE
    assert decision.suspect_chars == 3


def test_the_real_fixture_is_diverted_for_its_broken_ligature():
    """End to end, on the generated fixture: its font mis-maps lam-alef-hamza, so
    the document must not take the digital path even though it is born-digital."""
    from tests.fixtures import ensure_fixture

    decision = triage.classify(ensure_fixture().read_bytes())
    assert decision.route == triage.ROUTE_GEMINI
    assert decision.reason == triage.REASON_BROKEN_TOUNICODE


# ── Safety ───────────────────────────────────────────────────────────────────


def test_kill_switch_sends_everything_to_gemini(monkeypatch):
    monkeypatch.setattr(settings, "DIGITAL_PATH_ENABLED", False)
    decision = triage.classify(pdf_with_text(1))
    assert decision.route == triage.ROUTE_GEMINI
    assert decision.reason == triage.REASON_DISABLED


def test_unreadable_bytes_go_to_gemini_rather_than_raising():
    """Triage must never be the reason a conversion fails."""
    decision = triage.classify(b"this is not a pdf")
    assert decision.route == triage.ROUTE_GEMINI
    assert decision.reason == triage.REASON_UNREADABLE


def test_an_exception_mid_classification_still_returns_a_route(monkeypatch):
    def boom(page):
        raise RuntimeError("glyph table on fire")

    monkeypatch.setattr(triage, "_mark_counts", boom)
    decision = triage.classify(pdf_with_text(1))
    assert decision.route == triage.ROUTE_GEMINI
    assert decision.reason == triage.REASON_UNREADABLE


def test_decision_carries_the_producer_for_diagnosis():
    """Arabic breakage clusters by producer, so the route log has to name it."""
    decision = triage.classify(pdf_with_text(1))
    assert isinstance(decision.producer, str)
    assert decision.pages == 1


def test_triage_only_inspects_a_bounded_number_of_pages(monkeypatch):
    """A 600-page book is classified from its opening pages; this bounds triage,
    not the conversion."""
    monkeypatch.setattr(settings, "DIGITAL_TRIAGE_MAX_PAGES", 3)
    seen = []

    original = triage._page_is_text_bearing

    def counting(page):
        seen.append(1)
        return original(page)

    monkeypatch.setattr(triage, "_page_is_text_bearing", counting)
    decision = triage.classify(pdf_with_text(20))
    assert len(seen) == 3
    assert decision.pages == 20   # the real length is still reported
