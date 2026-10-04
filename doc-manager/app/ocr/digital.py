"""Born-digital extraction: read the text a PDF already contains.

Same contract as ``pipeline.process_pdf`` — PDF bytes in, DOCX bytes out — so the
worker can call either without caring which. No OCR, no network, no cost.

A PDF stores glyphs and coordinates, not paragraphs. Every library's "reading
order" is one guess at reassembling them, and on Arabic the guesses disagree:
measured on this corpus, pypdfium2 returns visual order (words reversed) and
pdf_oxide's default extractor reverses letters inside words. So the text is
rebuilt here from the glyph geometry rather than taken from any library's
``get_text``.

The layering, in order, each solving a failure observed on real documents:

  glyphs      drop space glyphs of zero width (classical typesetters emit one
              between every LETTER, which turns "وَلَيصح" into "و ل ي ص ح")
  lines       cluster by baseline, tolerance scaled to font size
  order       right-to-left by x, ligature groups (shared x) kept intact,
              combining marks bound to their base and emitted after it
  bidi        each Latin/digit token reversed back ("0051" -> "1500")
  structure   headings by COLOUR deviation, not size — real documents set
              headings in an accent colour at body size
  page        margins, border, printed page number, boilerplate images
"""

import io
import logging
import statistics
from collections import Counter
from dataclasses import dataclass, field

import fitz  # PyMuPDF

from app import metrics
from app.core.config import settings
from app.ocr.script import (
    is_combining_mark,
    is_latin_char,
    is_rtl_char,
    normalise_presentation_forms,
)
from app.ocr.styled_builder import (
    STYLE_SOURCE,
    Block,
    PageBorder,
    PageSetup,
    Run,
    build_styled_docx,
    map_font,
)

log = logging.getLogger("doc-worker.digital")

_FLAG_ITALIC = 1 << 1
_FLAG_BOLD = 1 << 4

import re  # noqa: E402  (kept beside the patterns it serves)

# "1-", "2.", "٣)" — a printed list numeral. The separator is required so a
# paragraph opening with a year is not mistaken for a list item.
_ORDERED_RE = re.compile(r"^((?:\d|[٠-٩]){1,3}\s*[-.)–])\s*(.+)$")
_BULLET_RE = re.compile(r"^[-*•●‣▪]\s*(.+)$")
_PAGE_NUM_RE = re.compile(r"^[\s\-–—]*([0-9٠-٩]{1,4})[\s\-–—]*$")


# ── Glyphs and lines ─────────────────────────────────────────────────────────


@dataclass
class Glyph:
    c: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    color: int
    flags: int
    font: str

    @property
    def baseline(self) -> float:
        return self.y1

    @property
    def bold(self) -> bool:
        return bool(self.flags & _FLAG_BOLD) or "bold" in self.font.lower()

    @property
    def italic(self) -> bool:
        return bool(self.flags & _FLAG_ITALIC) or "italic" in self.font.lower()

    def style_key(self) -> tuple:
        return (round(self.size, 1), self.color, self.bold, self.italic,
                map_font(self.font))


@dataclass
class Line:
    glyphs: list = field(default_factory=list)
    underline: bool = False

    @property
    def _inked(self) -> list:
        """Glyphs that actually mark the page. Leading and trailing spaces would
        otherwise stretch the line's extent and skew every alignment test."""
        return [g for g in self.glyphs if not g.c.isspace()] or self.glyphs

    @property
    def baseline(self) -> float:
        return statistics.median(g.baseline for g in self.glyphs)

    @property
    def size(self) -> float:
        sizes = [g.size for g in self.glyphs if not g.c.isspace()]
        return statistics.median(sizes) if sizes else 0.0

    @property
    def color(self) -> int:
        colors = [g.color for g in self.glyphs if not g.c.isspace()]
        return Counter(colors).most_common(1)[0][0] if colors else 0

    @property
    def bold(self) -> bool:
        weights = [g.bold for g in self.glyphs if not g.c.isspace()]
        return sum(weights) > len(weights) / 2 if weights else False

    @property
    def x0(self) -> float:
        return min(g.x0 for g in self._inked)

    @property
    def x1(self) -> float:
        return max(g.x1 for g in self._inked)

    @property
    def y0(self) -> float:
        return min(g.y0 for g in self._inked)


def read_glyphs(page) -> list[Glyph]:
    """Every glyph on the page with its box, size, colour, weight and font."""
    out: list[Glyph] = []
    for block in page.get_text("rawdict").get("blocks", []):
        if "lines" not in block:
            continue  # image block
        for line in block["lines"]:
            for span in line["spans"]:
                size = span.get("size", 0.0)
                color = span.get("color", 0)
                flags = span.get("flags", 0)
                font = span.get("font", "")
                for ch in span.get("chars", []):
                    c = ch.get("c")
                    # Some producers emit a glyph with no character at all; every
                    # downstream classifier calls ord() on it and dies.
                    if not c:
                        continue
                    # A space glyph of zero width is a kerning artifact, not a word
                    # break. Real spaces are kept — dropping those too and inferring
                    # every break from geometry fails the other way, because a
                    # non-connecting letter (ا د ر و) leaves an intra-word gap as
                    # wide as a real space.
                    x0, y0, x1, y1 = ch["bbox"]
                    if c.isspace() and (x1 - x0) < 0.5:
                        continue
                    out.append(Glyph(c, x0, y0, x1, y1, size, color, flags, font))
    return out


def cluster_lines(glyphs: list[Glyph], tol_ratio: float = 0.5) -> list[Line]:
    """Group glyphs into visual lines by baseline proximity.

    Tolerance scales with font size rather than being a fixed number of points, so
    a 24pt heading and 9pt footnote on the same page both cluster correctly.
    """
    if not glyphs:
        return []
    body = statistics.median([g.size for g in glyphs if not g.c.isspace()] or [10.0])
    tol = max(body * tol_ratio, 1.5)
    lines: list[Line] = []
    for g in sorted(glyphs, key=lambda g: g.baseline):
        for line in reversed(lines):
            if abs(line.baseline - g.baseline) <= tol:
                line.glyphs.append(g)
                break
        else:
            lines.append(Line([g]))
    return lines


# ── Underlines ───────────────────────────────────────────────────────────────


def find_rules(page) -> list[tuple[float, float, float]]:
    """Thin horizontal filled shapes — underlines, and page furniture."""
    out = []
    try:
        drawings = page.get_drawings()
    except Exception:  # noqa: BLE001 — a page we cannot read shapes from has none
        return out
    for d in drawings:
        r = d.get("rect")
        if r is not None and r.height <= 3.0 and r.width >= 15.0:
            out.append((r.y0, r.x0, r.x1))
    return out


def _rgb_hex(fill) -> str | None:
    """PyMuPDF reports colours as 0-1 floats; Word wants RRGGBB."""
    if not fill or len(fill) < 3:
        return None
    return "".join(f"{max(0, min(255, int(round(c * 255)))):02X}" for c in fill[:3])


def find_fills(page) -> list[tuple[tuple[float, float, float, float], str]]:
    """Filled rectangles big enough to sit behind text, as (rect, RRGGBB).

    A title band is a filled rectangle with the heading painted on top, and the
    text on it is routinely WHITE. Ignoring the fill therefore does not just lose a
    colour — it leaves white text on a white page and the heading disappears.

    Excludes thin rules (underlines, handled separately) and page-sized shapes
    (borders and full-page backgrounds, which would shade the entire document).
    """
    out = []
    try:
        drawings = page.get_drawings()
    except Exception:  # noqa: BLE001
        return out
    page_area = abs(page.rect.get_area()) or 1.0
    for d in drawings:
        r = d.get("rect")
        fill = d.get("fill")
        if r is None or fill is None:
            continue
        if r.height < 4.0 or r.width < 30.0:
            continue                      # a rule, not a band
        if abs(r.get_area()) / page_area > 0.5:
            continue                      # page background or frame
        hex_colour = _rgb_hex(fill)
        if hex_colour and hex_colour != "FFFFFF":
            out.append(((r.x0, r.y0, r.x1, r.y1), hex_colour))
    return out


def shading_for(line: Line, fills) -> str | None:
    """The fill a line sits on, if any. Nearest-enclosing wins, so a band inside a
    larger panel shades the line rather than the panel."""
    best, best_area = None, None
    for (fx0, fy0, fx1, fy1), colour in fills:
        if fx0 - 2 <= line.x0 and line.x1 <= fx1 + 2 and fy0 - 2 <= line.baseline <= fy1 + 2:
            area = (fx1 - fx0) * (fy1 - fy0)
            if best_area is None or area < best_area:
                best, best_area = colour, area
    return best


def mark_underlines(lines: list[Line], rules, page_width: float) -> None:
    """A rule under a line, covering most of its width, is an underline.

    Underlines in PDF are drawn rectangles, not a font flag. The search window
    straddles zero because a line's ``baseline`` here is the glyph box's BOTTOM,
    which includes descenders, while the rule sits at the typographic baseline —
    slightly above it.
    """
    for line in lines:
        span = line.x1 - line.x0
        if span <= 0:
            continue
        for y, rx0, rx1 in rules:
            if rx1 - rx0 > page_width * 0.9:
                continue  # a page frame, not an underline
            if not (-line.size * 0.35 <= y - line.baseline <= line.size * 0.7):
                continue
            if min(line.x1, rx1) - max(line.x0, rx0) > span * 0.5:
                line.underline = True
                break


# ── Ordering ─────────────────────────────────────────────────────────────────


def _is_ltr_token_char(ch: str) -> bool:
    """Characters that read left-to-right even inside an Arabic line.

    Digits of both families included: Unicode calls them weak types (EN/AN) and
    UAX #9 never reorders them within a run, so "1500" must stay "1500".
    """
    return ch.isdigit() or is_latin_char(ch)


def restore_ltr_tokens(ordered: list[Glyph]) -> list[Glyph]:
    """Undo the RTL sort inside each left-to-right token.

    Sorting by descending x is right for Arabic and wrong for every Latin word,
    number, IBAN and URL in the line, which come out backwards. Each token is
    reversed back: "0051" -> "1500", "RAS" -> "SAR", "41/6202-RH" -> "HR-2026/14".

    Tokens, not whole islands: reversing "0051 RAS" as one unit yields "SAR 1500" —
    characters right, words swapped. Which behaviour is correct depends on whether
    the producer laid the phrase out as a single bidi run, so this follows what the
    corpus's producers actually do and the fixture pins it.
    """
    out: list[Glyph] = []
    i, n = 0, len(ordered)
    while i < n:
        if not _is_ltr_token_char(ordered[i].c):
            out.append(ordered[i])
            i += 1
            continue
        j = last_strong = i
        while j < n:
            c = ordered[j].c
            if c.isspace() or is_rtl_char(c):
                break
            if _is_ltr_token_char(c):
                last_strong = j
            j += 1
        out.extend(reversed(ordered[i:last_strong + 1]))
        i = last_strong + 1
    return out


def attach_marks(glyphs: list[Glyph], rtl: bool) -> list[Glyph]:
    """Bind combining marks to their base letter, then order base-first.

    Tashkeel are zero-width glyphs with their own coordinates, and a mark's x sits
    at its base letter's leading edge. Ordering everything by position therefore
    emits the mark BEFORE the letter it belongs to, which renders "تَصَرُّف" as
    "َتصرف" — a loose fatha, then a bare word. So marks leave the positional sort,
    are matched to the nearest base, and re-emitted immediately after it: a
    grapheme cluster moves as one unit, which is what Word needs to shape the word.
    """
    bases = [g for g in glyphs if not is_combining_mark(g.c) and not g.c.isspace()]
    marks = [g for g in glyphs if is_combining_mark(g.c)]
    spaces = [g for g in glyphs if g.c.isspace() and not is_combining_mark(g.c)]
    if not bases:
        return sorted(glyphs, key=lambda g: g.x0, reverse=rtl)

    attached: dict[int, list[Glyph]] = {}
    for m in marks:
        best, best_d = None, None
        for i, b in enumerate(bases):
            d = 0.0 if b.x0 <= m.x0 <= b.x1 else min(abs(b.x1 - m.x0), abs(b.x0 - m.x0))
            if best_d is None or d < best_d:
                best, best_d = i, d
        if best is not None:
            attached.setdefault(best, []).append(m)

    order = sorted(range(len(bases)), key=lambda i: bases[i].x0, reverse=rtl)
    out: list[Glyph] = []
    for i in order:
        out.append(bases[i])
        out.extend(sorted(attached.get(i, []), key=lambda g: g.y0))

    # Real spaces return to their positional place among the bases.
    for sp in spaces:
        pos = 0
        for idx, g in enumerate(out):
            if is_combining_mark(g.c):
                continue
            if (g.x0 > sp.x0) if rtl else (g.x0 < sp.x0):
                pos = idx + 1
        out.insert(pos, sp)
    return out


def order_line(line: Line) -> tuple[list[Glyph], bool]:
    """Logical (reading) order for one line, and whether it is right-to-left."""
    strong = [g for g in line.glyphs
              if not g.c.isspace() and not is_combining_mark(g.c)]
    rtl = sum(1 for g in strong if is_rtl_char(g.c)) >= max(1, len(strong)) / 2
    ordered = attach_marks(line.glyphs, rtl)
    if rtl:
        ordered = restore_ltr_tokens(ordered)
    return ordered, rtl


def glyphs_to_runs(ordered: list[Glyph], rtl: bool, underline: bool,
                   style: str) -> list[Run]:
    """Collapse consecutive glyphs sharing an appearance into Word runs.

    One run per style change, not per glyph: a run per character inflates the file
    and stops Word shaping Arabic across the joins.
    """
    if not ordered:
        return []

    uniform = style != STYLE_SOURCE
    sizes = [g.size for g in ordered if not g.c.isspace()]
    em = statistics.median(sizes) if sizes else 10.0

    runs: list[Run] = []
    buf: list[str] = []
    key = None

    def flush() -> None:
        if buf and key is not None:
            size, color, bold, italic, font = key
            text = normalise_presentation_forms("".join(buf))
            if uniform:
                runs.append(Run(text, size=settings.DOCX_FONT_SIZE_PT, color=None,
                                bold=bold, italic=italic, underline=False,
                                font=settings.DOCX_FONT))
            else:
                runs.append(Run(text, size=size, color=color, bold=bold,
                                italic=italic, underline=underline, font=font))
        buf.clear()

    for i, g in enumerate(ordered):
        k = g.style_key()
        if key is None:
            key = k
        elif k != key:
            flush()
            key = k
        buf.append(g.c)

        # A geometric gap adds a break only where the producer emitted no real
        # space, so a properly-spaced line is left alone and a line whose spaces
        # were kerning artifacts still gets its words separated.
        if i + 1 < len(ordered) and not g.c.isspace():
            nxt = ordered[i + 1]
            if not nxt.c.isspace():
                gap = (g.x0 - nxt.x1) if rtl else (nxt.x0 - g.x1)
                if gap > em * settings.DIGITAL_WORD_GAP_EM:
                    buf.append(" ")
    flush()
    return runs


# ── Page-level structure ─────────────────────────────────────────────────────


def line_spacing(lines: list[Line], body_size: float) -> float:
    """The dominant baseline-to-baseline distance — the within-paragraph spacing.

    The MODE, not the median: paragraph breaks are a minority of gaps but a large
    one, and they drag a median upward until the threshold derived from it no
    longer separates them. Rounded to the point, because baselines carry sub-point
    jitter that would otherwise give every line its own "mode".
    """
    gaps = [round(lines[i + 1].baseline - lines[i].baseline)
            for i in range(len(lines) - 1)
            if 0 < lines[i + 1].baseline - lines[i].baseline < 200]
    if not gaps:
        return body_size * 1.4
    return float(Counter(gaps).most_common(1)[0][0])


def strip_leading(runs: list[Run], count: int) -> list[Run]:
    """Drop the first ``count`` characters, preserving each run's styling.

    Used to remove a printed bullet glyph. Word's List Bullet STYLE carries its own
    numPr and draws a bullet itself, so leaving the source's "•" in the text gives
    every item two of them.
    """
    out: list[Run] = []
    remaining = count
    for run in runs:
        if remaining <= 0:
            out.append(run)
            continue
        if len(run.text) <= remaining:
            remaining -= len(run.text)
            continue
        out.append(Run(run.text[remaining:], run.size, run.color, run.bold,
                       run.italic, run.underline, run.font))
        remaining = 0
    # Leading whitespace left behind by the glyph is not content either.
    while out and not out[0].text.strip():
        out.pop(0)
    if out:
        out[0] = Run(out[0].text.lstrip(), out[0].size, out[0].color, out[0].bold,
                     out[0].italic, out[0].underline, out[0].font)
    return out


def page_profile(lines: list[Line]) -> dict:
    """What "normal" looks like for a set of lines — the baseline every heading
    rule measures deviation from."""
    sizes, colors, weights = [], [], []
    for line in lines:
        n = len([g for g in line.glyphs if not g.c.isspace()])
        if not n:
            continue
        sizes += [line.size] * n
        colors += [line.color] * n
        weights += [line.bold] * n
    return {
        "size": statistics.median(sizes) if sizes else 10.0,
        "color": Counter(colors).most_common(1)[0][0] if colors else 0,
        "bold": (sum(weights) > len(weights) / 2) if weights else False,
    }


def text_column(lines: list[Line]) -> tuple[float, float]:
    """The body text column, as (left, right).

    Measured from FULL-WIDTH lines only, at percentiles rather than medians. Using
    every line lets a running head or a centred page number define the column;
    using medians lets the short last line of each justified paragraph drag the
    edge inward, which showed up as a constant asymmetry on genuinely centred text.
    """
    if not lines:
        return (0.0, 0.0)
    widths = [line.x1 - line.x0 for line in lines if line.size > 0]
    if not widths:
        return (min(ln.x0 for ln in lines), max(ln.x1 for ln in lines))
    widest = max(widths)
    full = [ln for ln in lines if ln.size > 0 and (ln.x1 - ln.x0) >= widest * 0.6]
    if not full:
        full = [ln for ln in lines if ln.size > 0]
    xs0 = sorted(ln.x0 for ln in full)
    xs1 = sorted(ln.x1 for ln in full)
    return (xs0[len(xs0) // 10], xs1[-1 - len(xs1) // 10])


def detect_align(line: Line, column: tuple[float, float],
                 page_width: float | None = None) -> str | None:
    """Centre, justified, or natural — from where the line sits on the page.

    Centring is tested against the midpoint of the text column AND of the page,
    accepting either. The column alone is not a safe reference: a document whose
    tables reach further right than its body text has an ASYMMETRIC column, and a
    title centred perfectly on the page then measures as 92pt off-centre against
    it. One real document centred its title at x=420.95 on an 842pt page — dead
    centre — while the column's midpoint sat at 467.

    Tolerance is 4% of the column width on the midpoint, which is the same 8% on
    the left-right gap difference: genuinely centred lines land within it, while
    right-aligned headings are 45-80% out.
    """
    left, right = column
    width = right - left
    if width <= 0:
        return None
    left_gap = line.x0 - left
    right_gap = right - line.x1
    inset = min(left_gap, right_gap)
    tolerance = width * 0.04

    if inset > width * 0.05:
        mid = (line.x0 + line.x1) / 2
        if abs(mid - (left + right) / 2) <= tolerance:
            return "center"
        if page_width and abs(mid - page_width / 2) <= tolerance:
            return "center"
    if left_gap < width * 0.03 and right_gap < width * 0.03:
        return "both"
    return None


def document_profile(doc, page_indexes) -> dict:
    all_lines: list[Line] = []
    for i in page_indexes:
        all_lines.extend(cluster_lines(read_glyphs(doc[i])))
    return page_profile(all_lines)


def document_column(doc, page_indexes) -> tuple[float, float]:
    """The body column across the WHOLE document.

    Per page this breaks exactly where centring matters most: on a title page every
    line is centred, so the widest centred line becomes the column and reads as
    justified; on a chapter divider the single line IS the column, so its gaps are
    zero and it reads as neither.
    """
    cols = []
    for i in page_indexes:
        lines = [ln for ln in cluster_lines(read_glyphs(doc[i])) if ln.size > 0]
        if len(lines) < 5:
            continue  # too sparse to describe a column
        left, right = text_column(lines)
        if right > left:
            cols.append((left, right))
    if not cols:
        return (0.0, 0.0)
    return (statistics.median(c[0] for c in cols),
            statistics.median(c[1] for c in cols))


def boilerplate_images(doc) -> set[int]:
    """Image xrefs appearing on most pages — watermarks, logos, page frames.

    Repetition beats size as a signal: this corpus's watermark covers only 27% of
    the page, so a coverage threshold misses it, but it is on all 48 pages.
    """
    seen: Counter = Counter()
    n = len(doc)
    for i in range(n):
        for xref in {img[0] for img in doc[i].get_images(full=True)}:
            seen[xref] += 1
    return {xref for xref, count in seen.items() if count >= max(2, n * 0.6)}


# ── Tables, margins, borders ─────────────────────────────────────────────────


def _is_decorative_grid(table, page_area: float) -> bool:
    """A page-sized "table" that is mostly empty is page decoration.

    The table finder keys off ruling lines, so a graphical page — a workbook cover,
    a certificate, a bordered worksheet — produces a grid covering the whole page.
    Accepting it is far more destructive than missing a real table: every line on
    the page becomes a cell, so paragraphs, headings and their alignment are gone.

    Both conditions are needed. Sparseness alone does not separate them — on this
    corpus a genuine 3x3 table was 11% filled while the decorative grids were 14% —
    but the real ones covered 1% of their page and the decorative ones 94%.
    """
    try:
        rect_area = abs(fitz.Rect(table.bbox).get_area())
        data = table.extract()
    except Exception:  # noqa: BLE001
        return False
    cells = sum(len(r) for r in data)
    if not cells:
        return True
    filled = sum(1 for r in data for c in r if (c or "").strip())
    return (rect_area / page_area) > 0.6 and (filled / cells) < 0.5


def extract_tables(page, glyphs: list[Glyph], style: str) -> list[dict]:
    """Ruled tables, each cell's text rebuilt from its own glyphs.

    The finder resolves the grid but returns cell text as the PDF paints it —
    visual order, presentation forms — so `الدرجة` arrives as `ةجردلا`. Running the
    cell's glyphs through the same ordering the body uses is what makes a cell read
    like a paragraph. Column order is left as the finder reports it; ``bidiVisual``
    on the table is what makes an RTL table read right-to-left in Word.
    """
    out = []
    try:
        found = page.find_tables()
    except Exception:  # noqa: BLE001
        return out

    page_area = abs(page.rect.get_area()) or 1.0
    for tb in getattr(found, "tables", []):
        if _is_decorative_grid(tb, page_area):
            continue
        rows_out = []
        try:
            row_objs = tb.rows
        except Exception:  # noqa: BLE001
            continue
        for r_i, row in enumerate(row_objs):
            cells_out = []
            for cell_bbox in row.cells:
                if not cell_bbox:
                    cells_out.append([])
                    continue
                cx0, cy0, cx1, cy1 = cell_bbox
                # Containment on the glyph's CENTRE, not its baseline: baseline is
                # the box's bottom edge, which for a glyph on a row's last line
                # falls inside the row below and drags that row's text in.
                inside = [g for g in glyphs
                          if cx0 <= (g.x0 + g.x1) / 2 <= cx1
                          and cy0 <= (g.y0 + g.y1) / 2 <= cy1]
                if not inside:
                    cells_out.append([])
                    continue
                runs: list[Run] = []
                for line in sorted(cluster_lines(inside), key=lambda ln: ln.baseline):
                    ordered, rtl = order_line(line)
                    runs.extend(glyphs_to_runs(ordered, rtl, line.underline, style))
                if r_i == 0:
                    runs = [Run(r.text, r.size, r.color, True, r.italic,
                                r.underline, r.font) for r in runs]
                cells_out.append(runs)
            rows_out.append(cells_out)

        if len(rows_out) >= 2 and any(any(c for c in r) for r in rows_out):
            out.append({"bbox": tuple(tb.bbox), "rows": rows_out})
    return out


def detect_margins(doc, page_indexes) -> tuple[float, float, float, float]:
    """Margins from where body text actually sits, as (top, bottom, left, right).

    Taken across pages at a percentile, and clamped: a sparsely-filled page (a
    title page, a chapter divider) leaves a large empty band that is white space,
    not margin, and one such page would otherwise set a 440pt bottom margin for the
    whole document.
    """
    lefts, rights, tops, bottoms = [], [], [], []
    for i in page_indexes:
        page = doc[i]
        lines = [ln for ln in cluster_lines(read_glyphs(page)) if ln.size > 0]
        if not lines:
            continue
        lefts.append(min(ln.x0 for ln in lines))
        rights.append(page.rect.width - max(ln.x1 for ln in lines))
        tops.append(min(ln.y0 for ln in lines))
        bottoms.append(page.rect.height - max(ln.baseline for ln in lines))

    page_h = doc[page_indexes[0]].rect.height if page_indexes else 842.0
    page_w = doc[page_indexes[0]].rect.width if page_indexes else 595.0

    def robust(values, fallback, limit):
        if not values:
            return fallback
        values = sorted(values)
        return max(18.0, min(values[len(values) // 4], limit))

    return (robust(tops, 72.0, page_h * 0.25), robust(bottoms, 72.0, page_h * 0.25),
            robust(lefts, 72.0, page_w * 0.30), robust(rights, 72.0, page_w * 0.30))


def detect_page_border(doc, page_indexes) -> PageBorder | None:
    """A frame drawn on most pages.

    Producers draw a "double" frame as several stacked filled bars rather than one
    bordered shape, so this measures the band from the outermost bar to the
    innermost. A frame may equally be one stroked rectangle, which is recorded as
    its own four edges.
    """
    votes = []
    for i in page_indexes:
        page = doc[i]
        W, H = page.rect.width, page.rect.height
        bars = []
        try:
            drawings = page.get_drawings()
        except Exception:  # noqa: BLE001
            continue
        for d in drawings:
            r = d.get("rect")
            if r is None:
                continue
            paint = d.get("fill") or d.get("color")
            if paint is None:
                continue
            if d.get("fill") is None and r.width > W * 0.85 and r.height > H * 0.85:
                lw = d.get("width") or 1.0
                bars += [
                    fitz.Rect(r.x0, r.y0, r.x1, r.y0 + lw),
                    fitz.Rect(r.x0, r.y1 - lw, r.x1, r.y1),
                    fitz.Rect(r.x0, r.y0, r.x0 + lw, r.y1),
                    fitz.Rect(r.x1 - lw, r.y0, r.x1, r.y1),
                ]
                continue
            if (r.width > W * 0.85 and r.height <= 6) or (r.height > H * 0.85 and r.width <= 6):
                bars.append(r)
        if len(bars) < 4:
            continue
        top_bars = [r for r in bars if r.width > W * 0.85 and r.y0 < H / 2]
        if not top_bars:
            continue
        outer = min(r.y0 for r in top_bars)
        inner = max(r.y1 for r in top_bars if r.y0 < outer + 12)
        votes.append((outer, inner - outer))

    if len(votes) < max(1, len(page_indexes) * 0.5):
        return None
    space = statistics.median(v[0] for v in votes)
    thickness = statistics.median(v[1] for v in votes)
    return PageBorder(
        style="thickThinSmallGap" if thickness > 2.0 else "single",
        size_eighths=int(round(max(2, min(96, thickness * 8)))),
        space_pt=int(round(space)),
    )


def detect_page_number_align(doc, page_indexes) -> str | None:
    """Where the printed page number sits, as a logical alignment."""
    seen = []
    for i in page_indexes:
        page = doc[i]
        W = page.rect.width
        for line in cluster_lines(read_glyphs(page)):
            if line.size <= 0 or line.y0 <= page.rect.y1 * 0.90:
                continue
            text = "".join(g.c for g in line.glyphs).strip()
            if not _PAGE_NUM_RE.match(text):
                continue
            mid = (line.x0 + line.x1) / 2
            if abs(mid - W / 2) < W * 0.12:
                seen.append("center")
            else:
                seen.append("start" if mid < W / 2 else "end")
    return Counter(seen).most_common(1)[0][0] if seen else None


# ── Page assembly ────────────────────────────────────────────────────────────


def extract_page(page, style: str, doc_profile: dict | None = None,
                 doc_column: tuple[float, float] | None = None
                 ) -> tuple[list[Block], str | None]:
    """One page's blocks, and its printed page number if it has one."""
    glyphs = read_glyphs(page)
    lines = cluster_lines(glyphs)
    lines.sort(key=lambda ln: ln.baseline)
    mark_underlines(lines, find_rules(page), page.rect.width)

    profile = page_profile(lines)
    # Too few lines for the page's own statistics to mean anything: a chapter
    # divider's single 72pt line IS its median, so nothing deviates from it.
    if doc_profile and len([ln for ln in lines if ln.size > 0]) < 5:
        profile = doc_profile
    column = (doc_column if (doc_column and doc_column[1] > doc_column[0])
              else text_column([ln for ln in lines if ln.size > 0]))

    tables = extract_tables(page, glyphs, style)
    fills = find_fills(page) if style == STYLE_SOURCE else []

    def in_table(line: Line) -> bool:
        return any(ty0 - 2 <= line.baseline <= ty1 + 2
                   for _, ty0, _, ty1 in (t["bbox"] for t in tables))

    normal_gap = line_spacing(lines, profile["size"])
    split_gap = max(normal_gap * settings.DIGITAL_PARA_GAP_RATIO, normal_gap + 1.5)

    blocks: list[Block] = []
    para_runs: list[Run] = []
    para_aligns: list[str] = []
    para_shading: list[str] = []
    page_label: str | None = None

    def flush() -> None:
        if para_runs:
            align = Counter(para_aligns).most_common(1)[0][0] if para_aligns else None
            shade = Counter(para_shading).most_common(1)[0][0] if para_shading else None
            blocks.append(Block("para", runs=list(para_runs), align=align, shading=shade))
            para_runs.clear()
            para_aligns.clear()
            para_shading.clear()

    for i, line in enumerate(lines):
        if in_table(line):
            continue
        ordered, rtl = order_line(line)
        runs = glyphs_to_runs(ordered, rtl, line.underline, style)
        text = "".join(r.text for r in runs).strip()
        if not text:
            continue

        if _PAGE_NUM_RE.match(text) and line.y0 > page.rect.y1 * 0.90:
            page_label = _PAGE_NUM_RE.match(text).group(1)
            continue

        align = detect_align(line, column, page.rect.width)
        shading = shading_for(line, fills)
        off_colour = line.color != profile["color"]
        bigger = line.size > profile["size"] * 1.15
        much_bigger = line.size > profile["size"] * 1.30

        bullet = _BULLET_RE.match(text)
        if bullet:
            flush()
            # The glyph goes; Word's List Bullet style supplies its own. The
            # printed NUMERAL of an ordered item is kept, because List Paragraph
            # carries no numbering and Word would otherwise re-render Arabic-Indic
            # digits as Western ones.
            marker = len(text) - len(bullet.group(1))
            blocks.append(Block("bullet", runs=strip_leading(runs, marker),
                                align=align, shading=shading))
            continue
        if _ORDERED_RE.match(text):
            flush()
            blocks.append(Block("ordered", runs=runs, align=align, shading=shading))
            continue

        # Colour is the strongest heading signal in real documents: an accent
        # colour at body size is a heading a size-only rule never sees. Centring is
        # the second: a short line set apart and only slightly larger than the body
        # is a title, and judging it on size alone misses it — one real document
        # set its section titles at 18pt against a 16pt body, 1.12x, under any
        # sane size threshold. A centred line cannot be a justified body line,
        # because centring requires an inset on BOTH sides.
        centred_title = align == "center" and line.size > profile["size"] * 1.02
        if (off_colour or much_bigger or centred_title
                or (bigger and line.bold and not profile["bold"])):
            flush()
            level = 1 if (much_bigger or (off_colour and bigger)) else 2
            blocks.append(Block("heading", runs=runs, level=level, align=align, shading=shading))
            continue

        if para_runs:
            para_runs.append(Run(" ", size=runs[0].size, font=runs[0].font))
        para_runs.extend(runs)
        if align:
            para_aligns.append(align)
        if shading:
            para_shading.append(shading)
        if i + 1 < len(lines) and lines[i + 1].baseline - line.baseline > split_gap:
            flush()
    flush()

    for t in tables:
        blocks.append(Block("table", rows=t["rows"], has_header_row=True))
    return blocks, page_label


# ── Entry point ──────────────────────────────────────────────────────────────


def process_pdf_digital(pdf_bytes: bytes, max_pages: int | None = None,
                        style: str = STYLE_SOURCE, mode: str = "ocr") -> bytes:
    """Raw PDF bytes in, raw DOCX bytes out — the same contract as the Gemini path.

    ``max_pages`` caps how many leading pages are converted (the anonymous trial
    uses it); ``mode`` only labels the metrics.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        n_total = len(doc)
        n_pages = min(n_total, max_pages) if max_pages else n_total
        indexes = list(range(n_pages))
        log.info("digital: %d of %d page(s), style=%s", n_pages, n_total, style)

        profile = document_profile(doc, indexes)
        column = document_column(doc, indexes)
        top, bottom, left, right = detect_margins(doc, indexes)
        border = detect_page_border(doc, indexes)
        number_align = detect_page_number_align(doc, indexes)

        pages: list[list[Block]] = []
        first_label: str | None = None
        for position, i in enumerate(indexes):
            blocks, label = extract_page(doc[i], style, profile, column)
            # The printed number belongs to the page it was found on: an unnumbered
            # title page means the label "2" on sheet two still implies the document
            # starts at 1.
            if label and first_label is None and label.isdigit():
                first_label = str(max(1, int(label) - position))
            pages.append(blocks)
            metrics.OCR_PAGES.labels(mode=mode).inc()

        setup = PageSetup(
            margin_top_pt=top, margin_bottom_pt=bottom,
            margin_left_pt=left, margin_right_pt=right,
            border=border, page_number_align=number_align,
            page_number_start=first_label,
        )
        buf = io.BytesIO()
        build_styled_docx(pages, buf, setup)
        return buf.getvalue()
    finally:
        doc.close()
