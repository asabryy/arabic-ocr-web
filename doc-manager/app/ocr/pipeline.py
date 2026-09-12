"""
Textara OCR pipeline — hosted Gemini vision backend.

PDF bytes in, DOCX bytes out. Each page is rendered to an image and sent to a
Google Gemini vision model with a plain "transcribe this Arabic page"
instruction; the returned text is assembled into a right-to-left Word document.

Replaces the former Qari / Qwen2-VL model that ran on Modal — no GPU, no torch,
no model loading. All OCR logic that is provider-agnostic (page rendering, DOCX
assembly) lives here so a different provider can be dropped in behind
``ocr_page`` without touching the worker.
"""

import io
import logging
import re
import time

import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from app import metrics
from app.core.config import settings

log = logging.getLogger("doc-worker.ocr")

OCR_PROMPT = (
    "You are an OCR engine for Arabic documents. Transcribe ALL text visible in "
    "this page image exactly as it appears. Preserve the original line breaks and "
    "right-to-left reading order. Do NOT translate, summarize, correct, or add "
    "anything. If a word is unreadable, transcribe your best guess. Output ONLY the "
    "raw transcribed text — no preamble, no commentary, no markdown fences."
)


# ── Page rendering ────────────────────────────────────────────────────────────

def render_page_png(page) -> bytes:
    """Render a PDF page to PNG bytes at the configured DPI (no PIL needed)."""
    mat = fitz.Matrix(settings.OCR_DPI / 72, settings.OCR_DPI / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    return pix.tobytes("png")


# ── OCR (Gemini) ──────────────────────────────────────────────────────────────

# Seams for tests (monkeypatch): the sleeper and the client factory.
_sleep = time.sleep
_client = None


def _get_client():
    """One genai.Client per process (reused across pages)."""
    global _client
    if _client is None:
        from google import genai

        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


_RETRY_HINT_RE = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


def _classify(exc: Exception) -> str:
    """'429' (rate limited), '503' (overloaded/unavailable) or 'other'."""
    code = getattr(exc, "code", None)
    msg = str(exc)
    if code == 429 or "RESOURCE_EXHAUSTED" in msg:
        return "429"
    if code == 503 or "UNAVAILABLE" in msg or "overloaded" in msg.lower():
        return "503"
    return "other"


def _retry_delay_seconds(exc: Exception) -> float | None:
    """Google's suggested wait: RetryInfo.retryDelay in the error details, else the
    'Please retry in 26.4s' phrase in the message. None if no hint."""
    details = getattr(exc, "details", None)
    try:
        entries = details["error"]["details"] if isinstance(details, dict) else []
        for entry in entries:
            if str(entry.get("@type", "")).endswith("RetryInfo"):
                delay = entry.get("retryDelay")
                if isinstance(delay, dict):
                    return float(delay.get("seconds", 0)) + float(delay.get("nanos", 0)) / 1e9
                if isinstance(delay, str) and delay.endswith("s"):
                    return float(delay[:-1])
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    m = _RETRY_HINT_RE.search(str(exc))
    return float(m.group(1)) if m else None


def ocr_page(png_bytes: bytes) -> str:
    """Run Gemini OCR on a single page image (PNG bytes), returning the text.

    Retries: 429 (rate limited) honouring Google's suggested delay, capped at
    OCR_429_MAX_DELAY_S, up to OCR_429_MAX_RETRIES times; 503/overloaded with linear
    backoff up to OCR_MAX_RETRIES. Anything else (or exhausted retries) raises, which
    fails the task and refunds the user's reserved pages.
    """
    from google.genai import types

    client = _get_client()
    model = settings.GEMINI_MODEL
    contents = [
        types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
        OCR_PROMPT,
    ]

    n429 = n503 = 0
    while True:
        t0 = time.perf_counter()
        try:
            resp = client.models.generate_content(model=model, contents=contents)
        except Exception as e:  # noqa: BLE001 — classified below
            kind = _classify(e)
            if kind == "429" and n429 < settings.OCR_429_MAX_RETRIES:
                n429 += 1
                hint = _retry_delay_seconds(e)
                delay = min(hint or settings.OCR_429_DEFAULT_DELAY_S * n429, settings.OCR_429_MAX_DELAY_S)
                metrics.GEMINI_REQUESTS.labels(outcome="retry_429", model=model).inc()
                metrics.GEMINI_BACKOFF_SECONDS.labels(reason="429").inc(delay)
                log.warning("Gemini 429 (attempt %d/%d) — sleeping %.1fs", n429, settings.OCR_429_MAX_RETRIES, delay)
                _sleep(delay)
                continue
            if kind == "503" and n503 < settings.OCR_MAX_RETRIES:
                n503 += 1
                delay = 2.0 * n503
                metrics.GEMINI_REQUESTS.labels(outcome="retry_503", model=model).inc()
                metrics.GEMINI_BACKOFF_SECONDS.labels(reason="503").inc(delay)
                log.warning("Gemini unavailable (attempt %d/%d) — sleeping %.1fs", n503, settings.OCR_MAX_RETRIES, delay)
                _sleep(delay)
                continue
            metrics.GEMINI_REQUESTS.labels(outcome="error", model=model).inc()
            raise

        metrics.GEMINI_REQUEST_DURATION.observe(time.perf_counter() - t0)
        metrics.GEMINI_REQUESTS.labels(outcome="ok", model=model).inc()
        metrics.record_gemini_usage(
            getattr(resp, "usage_metadata", None), model,
            settings.GEMINI_PRICE_INPUT_USD_PER_M, settings.GEMINI_PRICE_OUTPUT_USD_PER_M,
        )
        return (resp.text or "").strip()


# ── DOCX builder (RTL) ────────────────────────────────────────────────────────

def _set_rtl_paragraph(para) -> None:
    pPr = para._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)
    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def build_docx(pages_text: list[str], out) -> None:
    """Build a right-to-left DOCX from a list of per-page text strings."""
    doc = Document()

    sectPr = doc.sections[0]._sectPr
    sectPr.append(OxmlElement("w:bidi"))

    for page_num, text in enumerate(pages_text, 1):
        if page_num > 1:
            sep = doc.add_paragraph(f"-- Page {page_num} --")
            sep.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in sep.runs:
                run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
                run.font.size = Pt(9)

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                doc.add_paragraph("")
                continue
            para = doc.add_paragraph(line)
            _set_rtl_paragraph(para)
            for run in para.runs:
                run.font.name = "Arial"
                run.font.size = Pt(12)

    doc.save(out)


# ── Orchestration ─────────────────────────────────────────────────────────────

def process_pdf(pdf_bytes: bytes, max_pages: int | None = None, mode: str = "ocr") -> bytes:
    """Take raw PDF bytes, return raw DOCX bytes.

    ``max_pages`` caps how many leading pages are OCR'd (used by the anonymous trial).
    ``mode`` only labels the metrics (ocr|trial).
    """
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_total = len(pdf_doc)
    n_pages = min(n_total, max_pages) if max_pages else n_total
    log.info("OCR: %d of %d page(s) via %s", n_pages, n_total, settings.GEMINI_MODEL)

    pages_text: list[str] = []
    for i in range(n_pages):
        t0 = time.time()
        png = render_page_png(pdf_doc[i])
        text = ocr_page(png)
        elapsed = time.time() - t0
        metrics.OCR_PAGE_DURATION.observe(elapsed)
        metrics.OCR_PAGES.labels(mode=mode).inc()
        log.info("  page %d/%d — %d chars in %.1fs", i + 1, n_pages, len(text), elapsed)
        pages_text.append(text)
    pdf_doc.close()

    buf = io.BytesIO()
    build_docx(pages_text, buf)
    return buf.getvalue()
