"""
Textara OCR pipeline — hosted Gemini vision backend.

PDF bytes in, DOCX bytes out. Each page is rendered to an image and sent to a
Google Gemini vision model with a structured-transcription instruction; the
returned Markdown-ish text is parsed into blocks (paragraphs, headings, lists,
tables, running heads) and assembled into a real Word document.

Replaces the former Qari / Qwen2-VL model that ran on Modal — no GPU, no torch,
no model loading. All OCR logic that is provider-agnostic (page rendering, DOCX
assembly) lives here so a different provider can be dropped in behind
``ocr_page`` without touching the worker.
"""

import io
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field

import fitz  # PyMuPDF
from docx import Document
from docx.enum.table import WD_TABLE_DIRECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app import metrics
from app.core.config import settings

log = logging.getLogger("doc-worker.ocr")

# The marker the model is told to emit instead of guessing at illegible text.
ILLEGIBLE = "⟦?⟧"  # ⟦?⟧

OCR_PROMPT = f"""You are a document-transcription engine. Transcribe the page image \
into structured text, reproducing exactly what is printed. Never translate, \
summarise, correct, complete or explain it.

STRUCTURE
- Reconstruct logical paragraphs, not printed lines. When one sentence is wrapped over
  several printed lines, join those lines into a SINGLE line of output separated by
  single spaces. Separate consecutive paragraphs with one blank line.
- Keep a line break only where the layout means one: lines of poetry or verse, items of
  a list, rows of a table, lines of an address, and signature blocks.
- Headings (printed larger, bolder, or centred above a section): `# ` for the main
  heading of the page, `## ` for a sub-heading. One heading per line.
- Lists: `- ` for a bulleted item, `1. ` / `2. ` (keeping the printed numeral) for a
  numbered item. One item per line.
- Tables: a Markdown pipe table — `| cell | cell |` per row, with a `| --- | --- |`
  separator line after the header row. Keep the columns in their printed order.
- Multi-column pages: transcribe each column through to its end in reading order (for
  Arabic, the rightmost column first). Never read straight across the columns.

NON-BODY TEXT — mark it on its own line, never mix it into the body
- Running head at the top of the page:        [[header: ...]]
- Running foot at the bottom of the page:     [[footer: ...]]
- The printed page number, alone:             [[page: ...]]
- A block of footnotes at the foot of the page: the line [[footnotes]] on its own,
  then the notes, one per line.

FIDELITY
- Reproduce tashkeel (harakat) exactly as printed: do not add vowel marks that are not
  there, and do not drop ones that are.
- Reproduce digits in the script actually printed. Arabic-Indic digits
  (٠١٢٣٤٥٦٧٨٩) stay Arabic-Indic; \
Western digits (0123456789) stay
  Western. Never convert one into the other.
- Keep Latin-script words, names, numbers and references exactly as printed.
- NEVER guess. If a word is genuinely illegible — torn, blurred, smudged, cut off or
  covered — output {ILLEGIBLE} in its place, one {ILLEGIBLE} per illegible word. A confident
  wrong reading is far worse than a marked gap: do not infer a plausible word from
  context, and do not silently omit it.
- If the page contains no text at all, output nothing.

Output ONLY the transcription: no preamble, no commentary, no code fences."""


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
    """'429' (rate limited), '503' (overloaded/unavailable) or 'other'.

    Order matters: a depleted-billing 402 also carries a RESOURCE_EXHAUSTED status, so it
    has to be matched before the 429 rule — retrying it just burns minutes per page and
    fails anyway. It needs an operator to top up credits, so fail fast and surface it.
    """
    code = getattr(exc, "code", None)
    msg = str(exc)
    if code == 402:
        return "other"
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


# ── Script / direction detection ──────────────────────────────────────────────

# Arabic (+ supplements and presentation forms), Hebrew, Syriac, Thaana, N'Ko:
# everything Word must lay out right-to-left.
_RTL_RANGES = (
    (0x0590, 0x05FF),  # Hebrew
    (0x0600, 0x06FF),  # Arabic
    (0x0700, 0x074F),  # Syriac
    (0x0750, 0x077F),  # Arabic Supplement
    (0x0780, 0x07BF),  # Thaana
    (0x07C0, 0x07FF),  # N'Ko
    (0x0860, 0x08FF),  # Syriac Supplement / Arabic Extended-A
    (0xFB1D, 0xFDFF),  # Hebrew + Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
)


def _is_rtl_char(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _RTL_RANGES)


def _is_latin_char(ch: str) -> bool:
    cp = ord(ch)
    if not ch.isalpha():
        return False
    return (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A) or (0x00C0 <= cp <= 0x024F)


def _char_script(ch: str) -> str | None:
    """'rtl', 'ltr', or None for a neutral character (space, digit, punctuation)."""
    if _is_rtl_char(ch):
        # Combining marks (tashkeel) inherit the direction of what they sit on, but
        # they only ever sit on Arabic letters here, so counting them as RTL is safe.
        return "rtl"
    if _is_latin_char(ch):
        return "ltr"
    return None


def is_rtl_text(text: str, default: bool = True) -> bool:
    """True when a string is majority right-to-left.

    Counted per WORD — each token takes the direction of its first strong character —
    not per character: Arabic words are markedly shorter than their Latin equivalents,
    so a character count flips "نص Smith" to left-to-right on spelling alone. Text with
    no strong characters at all (a numeric table cell, a date) falls back to ``default``,
    the surrounding direction, rather than being forced left-to-right.
    """
    rtl = ltr = 0
    for token in text.split():
        for ch in token:
            script = _char_script(ch)
            if script == "rtl":
                rtl += 1
                break
            if script == "ltr":
                ltr += 1
                break
    if rtl == ltr:
        return default
    return rtl > ltr


def _segment_by_script(text: str, default_rtl: bool) -> list[tuple[str, bool]]:
    """Split text into (chunk, is_rtl) runs at strong-direction boundaries.

    Neutral characters attach to the chunk that precedes them (or to the first strong
    chunk when they lead), so "قال Smith في 1998" becomes an RTL run, an LTR run and an
    RTL run — each of which can then carry (or not carry) ``<w:rtl/>``.
    """
    if not text:
        return []
    chunks: list[list] = []  # [text, is_rtl|None]
    for ch in text:
        script = _char_script(ch)
        want = None if script is None else (script == "rtl")
        if chunks and (want is None or chunks[-1][1] in (None, want)):
            chunks[-1][0] += ch
            if chunks[-1][1] is None and want is not None:
                chunks[-1][1] = want
        else:
            chunks.append([ch, want])
    return [(t, default_rtl if d is None else d) for t, d in chunks]


# ── Structured-text parsing ───────────────────────────────────────────────────

_MARKER_RE = re.compile(
    r"^\[\[\s*(header|footer|page|footnote|footnotes)\s*(?::\s*(.*?))?\s*\]\]$",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
_BULLET_RE = re.compile(r"^(\s*)[-*•●‣]\s+(.*)$")
# The trailing separator is mandatory and the numeral capped at three digits, so an
# ordinary paragraph opening with a year ("1998 كان…") is not mistaken for a list item.
_ORDERED_RE = re.compile(r"^(\s*)((?:\d|[٠-٩۰-۹]){1,3}[.)۔-])\s+(.+)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_FENCE_RE = re.compile(r"^\s*```+\s*\w*\s*$")
_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩"
                              "۰۱۲۳۴۵۶۷۸۹",
                              "01234567890123456789")


@dataclass
class Block:
    """One renderable unit of a page."""

    kind: str  # "para" | "heading" | "bullet" | "ordered" | "table" | "rule"
    lines: list[str] = field(default_factory=list)
    level: int = 0                      # heading level, or list nesting depth
    rows: list[list[str]] = field(default_factory=list)
    has_header_row: bool = False
    small: bool = False                 # footnote zone — rendered a size down


@dataclass
class Page:
    """A parsed page: body blocks plus the running heads lifted out of the body."""

    blocks: list[Block] = field(default_factory=list)
    header: str | None = None
    footer: str | None = None
    page_label: str | None = None


def _split_table_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return [c.replace("\\|", "|").strip() for c in cells]


def _parse_page(text: str) -> Page:
    """Turn one page of model output into a Page of blocks.

    Lines within a block become hard line breaks; blank lines end a block. The model is
    instructed to join lines it wrapped mid-sentence, so a line break that survives here
    is a deliberate one (verse, an address, a signature) and is preserved as such — no
    heuristic re-flow is attempted, because guessing wrong would silently destroy poetry.
    """
    page = Page()
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i, n = 0, len(lines)
    small = False
    para: list[str] = []

    def flush() -> None:
        nonlocal para
        if para:
            page.blocks.append(Block("para", lines=para, small=small))
            para = []

    while i < n:
        raw = lines[i]
        line = raw.strip()

        if not line or _FENCE_RE.match(raw):
            flush()
            i += 1
            continue

        marker = _MARKER_RE.match(line)
        if marker:
            flush()
            kind, value = marker.group(1).lower(), (marker.group(2) or "").strip()
            if kind == "header" and value:
                page.header = page.header or value
            elif kind == "footer" and value:
                page.footer = page.footer or value
            elif kind == "page":
                page.page_label = page.page_label or value
            else:  # footnote(s) separator
                small = True
                page.blocks.append(Block("rule"))
            i += 1
            continue

        if _TABLE_ROW_RE.match(line):
            flush()
            rows, has_header = [], False
            while i < n and _TABLE_ROW_RE.match(lines[i].strip()):
                row = lines[i].strip()
                if _TABLE_SEP_RE.match(row):
                    has_header = bool(rows)
                else:
                    rows.append(_split_table_row(row))
                i += 1
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                page.blocks.append(Block("table", rows=rows, has_header_row=has_header, small=small))
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            flush()
            page.blocks.append(
                Block("heading", lines=[heading.group(2)], level=len(heading.group(1)), small=small)
            )
            i += 1
            continue

        bullet = _BULLET_RE.match(raw)
        if bullet:
            flush()
            depth = min(len(bullet.group(1)) // 2, 2)
            page.blocks.append(Block("bullet", lines=[bullet.group(2).strip()], level=depth, small=small))
            i += 1
            continue

        ordered = _ORDERED_RE.match(raw)
        if ordered:
            flush()
            depth = min(len(ordered.group(1)) // 2, 2)
            # The printed numeral is kept verbatim: Word's own numbering would re-render
            # Arabic-Indic digits as Western ones, undoing the digit fidelity the prompt
            # works for.
            label = ordered.group(2) + " "
            page.blocks.append(
                Block("ordered", lines=[label + ordered.group(3).strip()], level=depth, small=small)
            )
            i += 1
            continue

        para.append(line)
        i += 1

    flush()
    return page


# ── Low-level OOXML helpers ───────────────────────────────────────────────────

# Child order is not optional in OOXML: Word rejects (or silently ignores) properties
# written out of schema sequence, which is how `w:cs` can "be set" and do nothing.
_PPR_SEQ = (
    "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
    "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs",
    "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
    "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
    "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
    "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
    "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
    "w:pPrChange",
)
_SECTPR_SEQ = (
    "w:footnotePr", "w:endnotePr", "w:type", "w:pgSz", "w:pgMar", "w:paperSrc",
    "w:pgBorders", "w:lnNumType", "w:pgNumType", "w:cols", "w:formProt", "w:vAlign",
    "w:noEndnote", "w:titlePg", "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid",
    "w:printerSettings", "w:sectPrChange",
)
_RPR_SEQ = (
    "w:rStyle", "w:rFonts", "w:b", "w:bCs", "w:i", "w:iCs", "w:caps", "w:smallCaps",
    "w:strike", "w:dstrike", "w:outline", "w:shadow", "w:emboss", "w:imprint",
    "w:noProof", "w:snapToGrid", "w:vanish", "w:webHidden", "w:color", "w:spacing",
    "w:w", "w:kern", "w:position", "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect",
    "w:bdr", "w:shd", "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang",
    "w:eastAsianLayout", "w:specVanish", "w:oMath",
)


def _set_child(parent, seq: tuple[str, ...], tag: str, **attrs: str):
    """Replace ``tag`` under ``parent``, inserted at its schema-mandated position."""
    parent.remove_all(tag)
    el = OxmlElement(tag)
    for name, value in attrs.items():
        el.set(qn(name), value)
    successors = seq[seq.index(tag) + 1:] if tag in seq else ()
    parent.insert_element_before(el, *successors)
    return el


def _half_points(size_pt: float) -> str:
    return str(int(round(size_pt * 2)))


def _add_run(para, text: str, *, rtl: bool, size_pt: float,
             bold: bool = False, highlight: bool = False):
    """Append one run carrying BOTH the Latin and the complex-script properties.

    ``python-docx``'s ``run.font.name`` writes only ``w:ascii``/``w:hAnsi`` and
    ``run.font.size`` only ``w:sz`` — Word lays Arabic out from ``w:cs``/``w:szCs``,
    so a run styled through the high-level API renders in Word's default font at
    Word's default size. Everything here is written on the XML directly.
    """
    run = para.add_run(text)
    rPr = run._r.get_or_add_rPr()
    font = settings.DOCX_FONT
    _set_child(rPr, _RPR_SEQ, "w:rFonts", **{"w:ascii": font, "w:hAnsi": font, "w:cs": font})
    if bold:
        # w:bCs is the complex-script half of bold; w:b alone leaves Arabic un-bolded.
        _set_child(rPr, _RPR_SEQ, "w:b")
        _set_child(rPr, _RPR_SEQ, "w:bCs")
    _set_child(rPr, _RPR_SEQ, "w:sz", **{"w:val": _half_points(size_pt)})
    _set_child(rPr, _RPR_SEQ, "w:szCs", **{"w:val": _half_points(size_pt)})
    if highlight:
        _set_child(rPr, _RPR_SEQ, "w:highlight", **{"w:val": "yellow"})
    if rtl:
        # <w:rtl/> marks the run right-to-left; without it Word resolves the run with
        # the paragraph's base direction only and mis-places neutrals and numerals.
        _set_child(rPr, _RPR_SEQ, "w:rtl")
    return run


def _add_break(para, kind: str | None = None) -> None:
    br = OxmlElement("w:br")
    if kind:
        br.set(qn("w:type"), kind)
    run = para.add_run()
    run._r.append(br)


def _split_bold(text: str) -> list[tuple[str, bool]]:
    """`**bold**` / `__bold__` → (chunk, is_bold). Markdown emphasis the model emits
    anyway would otherwise reach the reader as literal asterisks."""
    out: list[tuple[str, bool]] = []
    pos = 0
    for m in _BOLD_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(1) or m.group(2) or "", True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out or [(text, False)]


def _add_inline(para, text: str, *, rtl: bool, size_pt: float, bold: bool = False) -> None:
    """Render one line of text into ``para`` as correctly-directed, correctly-fonted runs."""
    for chunk, is_bold in _split_bold(text):
        for piece in re.split(f"({re.escape(ILLEGIBLE)})", chunk):
            if not piece:
                continue
            if piece == ILLEGIBLE:
                # Highlighted so a human proof-reader can find every gap the model
                # refused to guess at.
                _add_run(para, piece, rtl=rtl, size_pt=size_pt, bold=bold, highlight=True)
                continue
            for seg, seg_rtl in _segment_by_script(piece, rtl):
                _add_run(para, seg, rtl=seg_rtl, size_pt=size_pt, bold=bold or is_bold)


def _direct_paragraph(para, rtl: bool) -> None:
    """Set the paragraph's base direction and matching alignment.

    A Latin-majority paragraph gets ``w:bidi w:val="0"`` and left alignment, so English
    or French inside an Arabic document is not dragged to the right margin.
    """
    pPr = para._p.get_or_add_pPr()
    _set_child(pPr, _PPR_SEQ, "w:bidi", **{"w:val": "1" if rtl else "0"})
    para.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl else WD_ALIGN_PARAGRAPH.LEFT


def _render_lines(para, lines: list[str], *, rtl: bool, size_pt: float, bold: bool = False) -> None:
    for idx, line in enumerate(lines):
        if idx:
            _add_break(para)
        _add_inline(para, line, rtl=rtl, size_pt=size_pt, bold=bold)


# ── Block renderers ───────────────────────────────────────────────────────────

_LIST_BULLET_STYLES = ("List Bullet", "List Bullet 2", "List Bullet 3")


def _render_table(doc, block: Block, size_pt: float, default_rtl: bool) -> None:
    rows = block.rows
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    try:
        table.style = "Table Grid"
    except KeyError:  # pragma: no cover — style is present in the default template
        pass
    table_rtl = is_rtl_text(" ".join(c for r in rows for c in r), default=default_rtl)
    if table_rtl:
        # Without bidiVisual Word draws the first column on the LEFT, mirroring the
        # source table's column order.
        table.table_direction = WD_TABLE_DIRECTION.RTL
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            para = table.cell(r, c).paragraphs[0]
            cell_rtl = is_rtl_text(text, default=table_rtl)
            _direct_paragraph(para, cell_rtl)
            _add_inline(para, text, rtl=cell_rtl, size_pt=size_pt,
                        bold=block.has_header_row and r == 0)
    doc.add_paragraph()


def _render_rule(doc) -> None:
    """The footnote separator: a short rule, as printed above notes on the page."""
    para = doc.add_paragraph()
    pPr = para._p.get_or_add_pPr()
    bdr = _set_child(pPr, _PPR_SEQ, "w:pBdr")
    top = OxmlElement("w:top")
    for name, value in (("w:val", "single"), ("w:sz", "4"), ("w:space", "1"), ("w:color", "auto")):
        top.set(qn(name), value)
    bdr.append(top)
    _set_child(pPr, _PPR_SEQ, "w:spacing", **{"w:before": "120", "w:after": "0"})


def _render_block(doc, block: Block, default_rtl: bool) -> None:
    body_pt = settings.DOCX_FONT_SIZE_PT
    size_pt = settings.DOCX_FOOTNOTE_SIZE_PT if block.small else body_pt

    if block.kind == "rule":
        _render_rule(doc)
        return

    if block.kind == "table":
        _render_table(doc, block, size_pt, default_rtl)
        return

    text = " ".join(block.lines)
    rtl = is_rtl_text(text, default=default_rtl)

    if block.kind == "heading":
        level = min(block.level, 2)
        para = doc.add_paragraph(style=f"Heading {level}")
        _direct_paragraph(para, rtl)
        # Heading styles carry a Latin theme font and a colour; the complex-script side
        # is still unset, so the runs are styled explicitly here too.
        _render_lines(para, block.lines, rtl=rtl,
                      size_pt=body_pt + (4 if level == 1 else 2), bold=True)
        return

    if block.kind == "bullet":
        para = doc.add_paragraph(style=_LIST_BULLET_STYLES[min(block.level, 2)])
    elif block.kind == "ordered":
        para = doc.add_paragraph(style="List Paragraph")
    else:
        para = doc.add_paragraph()

    _direct_paragraph(para, rtl)
    _render_lines(para, block.lines, rtl=rtl, size_pt=size_pt)


# ── Section / running heads ───────────────────────────────────────────────────

# A4 in twentieths of a point: 210 × 297 mm.
A4_WIDTH_TWIPS = 11906
A4_HEIGHT_TWIPS = 16838


def _configure_section(section, default_rtl: bool) -> None:
    sectPr = section._sectPr
    _set_child(sectPr, _SECTPR_SEQ, "w:pgSz",
               **{"w:w": str(A4_WIDTH_TWIPS), "w:h": str(A4_HEIGHT_TWIPS)})
    if default_rtl:
        _set_child(sectPr, _SECTPR_SEQ, "w:bidi", **{"w:val": "1"})


def _most_common(values: list[str]) -> str | None:
    values = [v for v in values if v]
    return Counter(values).most_common(1)[0][0] if values else None


def _hdrftr_paragraph(container):
    """The (single) paragraph of a header/footer definition, created if need be."""
    paragraphs = container.paragraphs
    para = paragraphs[0] if paragraphs else container.add_paragraph()
    para.clear()
    return para


def _fill_hdrftr(container, text: str, default_rtl: bool) -> None:
    para = _hdrftr_paragraph(container)
    rtl = is_rtl_text(text, default=default_rtl)
    _direct_paragraph(para, rtl)
    _add_inline(para, text, rtl=rtl, size_pt=settings.DOCX_FOOTNOTE_SIZE_PT)


def _add_page_field(container, default_rtl: bool) -> None:
    """A real PAGE field, so Word re-numbers correctly as the user edits."""
    para = _hdrftr_paragraph(container)
    _direct_paragraph(para, default_rtl)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    placeholder = _add_run(para, "1", rtl=False, size_pt=settings.DOCX_FOOTNOTE_SIZE_PT)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), " PAGE ")
    fld.append(placeholder._r)  # re-parents the run into the field
    para._p.append(fld)


def _apply_running_heads(section, pages: list[Page], default_rtl: bool) -> None:
    """Running heads, running feet and printed page numbers leave the body text.

    One Word section carries one header and one footer, so the value repeated on most
    pages wins and the rest are dropped — they are boilerplate by definition. The
    printed page number never becomes body text: it sets the starting number of a real
    PAGE field instead, so the document's numbering matches the original's.
    """
    header = _most_common([p.header for p in pages if p.header])
    footer = _most_common([p.footer for p in pages if p.footer])
    if header:
        _fill_hdrftr(section.header, header, default_rtl)

    labels = [p.page_label for p in pages if p.page_label]
    if footer:
        _fill_hdrftr(section.footer, footer, default_rtl)
    elif labels:
        _add_page_field(section.footer, default_rtl)

    if labels:
        first = labels[0].translate(_ARABIC_INDIC).strip()
        if first.isdigit() and 0 < int(first) < 32768:
            _set_child(section._sectPr, _SECTPR_SEQ, "w:pgNumType", **{"w:start": first})


# ── DOCX builder ──────────────────────────────────────────────────────────────

def build_docx(pages_text: list[str], out) -> None:
    """Build a Word document from a list of per-page model transcriptions.

    The model's structured output (paragraphs, `#` headings, `-` lists, pipe tables,
    `[[header:]]` / `[[footer:]]` / `[[page:]]` markers) becomes real Word constructs:
    A4 pages, `<w:tbl>` tables, page breaks, headings and lists, with complex-script
    font and size on every run and per-paragraph direction.
    """
    pages = [_parse_page(t) for t in pages_text]
    body_text = "\n".join(
        " ".join(b.lines) + " " + " ".join(c for r in b.rows for c in r)
        for p in pages for b in p.blocks
    )
    default_rtl = is_rtl_text(body_text, default=True)

    doc = Document()
    section = doc.sections[0]
    _configure_section(section, default_rtl)
    _apply_running_heads(section, pages, default_rtl)

    for index, page in enumerate(pages):
        if index:
            _add_break(doc.add_paragraph(), "page")
        for block in page.blocks:
            _render_block(doc, block, default_rtl)

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
