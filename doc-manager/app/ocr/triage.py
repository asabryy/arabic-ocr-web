"""Decide which conversion path a PDF should take.

Textara has two routes: a digital one that reads the text layer the PDF already
carries (free, milliseconds) and a Gemini vision one that reads a rendered image
(~$0.0036 and 3-9 s per page). This module picks between them, before either runs,
from signals that cost one pass over the document's glyphs.

Every rule here was measured against 293 real user documents (11,336 pages):
71% are born-digital, and of those 76% extract cleanly. The rest carry defects
that no amount of geometry recovers, and the honest response is to pay for OCR
rather than hand back plausible-looking wrong text.
"""

import logging
from collections import Counter
from dataclasses import dataclass

import fitz  # PyMuPDF

from app.core.config import settings
from app.ocr.script import is_combining_mark, is_rtl_char

log = logging.getLogger("doc-worker.triage")

ROUTE_DIGITAL = "digital"
ROUTE_GEMINI = "gemini"

# Reasons, used as metric labels — keep them short and stable.
REASON_CLEAN = "clean"
REASON_NO_TEXT_LAYER = "no_text_layer"
REASON_BATCHED_TASHKEEL = "batched_tashkeel"
REASON_BROKEN_TOUNICODE = "broken_tounicode"
REASON_DISABLED = "disabled"
REASON_UNREADABLE = "unreadable"

# A page needs this much text before it counts as text-bearing rather than a
# caption on a scan.
_MIN_PAGE_CHARS = 50


@dataclass(frozen=True)
class Triage:
    route: str
    reason: str
    pages: int = 0
    text_pages: int = 0
    producer: str = ""
    mark_batching: float = 0.0
    suspect_chars: int = 0

    @property
    def is_digital(self) -> bool:
        return self.route == ROUTE_DIGITAL


def _page_is_text_bearing(page) -> bool:
    return len("".join(page.get_text("text").split())) >= _MIN_PAGE_CHARS


def _mark_counts(page) -> tuple[int, int]:
    """(marks on this page, marks sharing a coordinate with another).

    Returned as COUNTS so a caller can pool them across the document. A per-page
    ratio is neither poolable nor trustworthy: a page carrying two marks that
    happen to collide scores 100%, and taking the worst page then condemns the
    document. On the corpus, per-page-max flagged 42% of documents where pooling
    flags 23% — the difference is entirely false positives.
    """
    seen: Counter = Counter()
    total = 0
    for block in page.get_text("rawdict").get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                for ch in span.get("chars", []):
                    c = ch.get("c")
                    if c and is_combining_mark(c):
                        seen[(round(ch["bbox"][1], 1), round(ch["bbox"][0], 1))] += 1
                        total += 1
    return total, sum(n - 1 for n in seen.values() if n > 1)


def _suspect_chars(page) -> int:
    """Characters that betray a broken ToUnicode map.

    A font whose cmap is wrong decodes a plausible glyph to an unrelated
    codepoint — NotoNaskhArabic maps its lam-alef-hamza ligature to U+01C2, a
    Latin click consonant, so `الأولى` extracts as `اǂولى`. Every extractor
    produces the same garbage, so the page goes to OCR rather than being guessed
    at: a confident wrong reading is worse than a marked gap, which is the rule
    the Gemini prompt already follows.
    """
    text = page.get_text("text")
    n = 0
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch.isspace() or ch.isdigit() or is_rtl_char(ch):
            continue
        cp = ord(ch)
        # ASCII and Latin-1 are legitimately present in Arabic documents.
        if cp < 0x0100 or not (0x0100 <= cp <= 0x024F) or not ch.isalpha():
            continue
        prev = chars[i - 1] if i else ""
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if is_rtl_char(prev) or is_rtl_char(nxt):
            n += 1
    return n


def classify(pdf_bytes: bytes, max_pages: int | None = None) -> Triage:
    """Pick a route for this PDF. Never raises — an unreadable file goes to Gemini.

    ``max_pages`` bounds the inspection, not the conversion: a 600-page book is
    classified from its opening pages rather than paying a full pass to decide.
    """
    if not settings.DIGITAL_PATH_ENABLED:
        return Triage(ROUTE_GEMINI, REASON_DISABLED)

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:  # noqa: BLE001 — a file we cannot parse is Gemini's problem
        log.warning("Triage could not open the PDF (%s); routing to Gemini", e)
        return Triage(ROUTE_GEMINI, REASON_UNREADABLE)

    try:
        n_pages = len(doc)
        limit = min(n_pages, max_pages or settings.DIGITAL_TRIAGE_MAX_PAGES)
        meta = doc.metadata or {}
        producer = (meta.get("producer") or meta.get("creator") or "unknown").strip()[:60]

        text_pages = 0
        marks_total = marks_dup = 0
        suspect = 0
        for i in range(limit):
            page = doc[i]
            if _page_is_text_bearing(page):
                text_pages += 1
            m, d = _mark_counts(page)
            marks_total += m
            marks_dup += d
            suspect += _suspect_chars(page)

        ratio = text_pages / limit if limit else 0.0
        batching = (
            marks_dup / marks_total
            if marks_total >= settings.DIGITAL_MIN_MARKS_FOR_BATCHING
            else 0.0
        )

        common = dict(pages=n_pages, text_pages=text_pages, producer=producer,
                      mark_batching=round(batching, 3), suspect_chars=suspect)

        if ratio < settings.DIGITAL_MIN_TEXT_PAGE_RATIO:
            return Triage(ROUTE_GEMINI, REASON_NO_TEXT_LAYER, **common)
        if batching > settings.DIGITAL_MAX_MARK_BATCHING:
            return Triage(ROUTE_GEMINI, REASON_BATCHED_TASHKEEL, **common)
        if suspect > 0:
            return Triage(ROUTE_GEMINI, REASON_BROKEN_TOUNICODE, **common)
        return Triage(ROUTE_DIGITAL, REASON_CLEAN, **common)
    except Exception as e:  # noqa: BLE001 — triage must never fail a conversion
        log.warning("Triage failed (%s); routing to Gemini", e)
        return Triage(ROUTE_GEMINI, REASON_UNREADABLE)
    finally:
        doc.close()
