"""Digital extraction, asserted against a document whose correct answer is known.

Every assertion here corresponds to a bug that was real: each one failed before
the rule it guards was written. They are golden tests rather than snapshots —
the expected strings are the fixture's own source text, not a previous run's
output, so a regression cannot be "fixed" by re-recording it.
"""

import html
import io
import re
import zipfile

import fitz
import pytest

from app.ocr.digital import process_pdf_digital
from app.ocr.styled_builder import STYLE_SOURCE, STYLE_UNIFORM
from tests.fixtures import (
    EXPECT_BAND_FILL,
    EXPECT_BAND_TITLE,
    EXPECT_BODY,
    EXPECT_MIXED_LINE,
    EXPECT_REFERENCE,
    EXPECT_TABLE_HEADER,
    EXPECT_TABLE_ROWS,
    REJECT,
    ensure_fixture,
)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    return ensure_fixture().read_bytes()


def document_xml(docx: bytes) -> str:
    return zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml").decode()


def all_text(docx: bytes) -> str:
    """Every text node joined with nothing between them — runs split at style and
    script boundaries, so a separator would break strings that are contiguous in
    the document."""
    xml = document_xml(docx)
    return "".join(
        html.unescape(t) for t in re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)
    ).replace(" ", " ")


def table_rows(docx: bytes) -> list[list[str]]:
    xml = document_xml(docx)
    rows = []
    for tr in re.findall(r"<w:tr[ >].*?</w:tr>", xml, re.S):
        cells = [
            "".join(html.unescape(t) for t in re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc))
            .replace(" ", " ").strip()
            for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S)
        ]
        rows.append(cells)
    return rows


# ── Bidi ─────────────────────────────────────────────────────────────────────


def test_digits_keep_their_order_inside_an_arabic_line(fixture_bytes):
    """Unicode calls digits weak types; UAX #9 never reorders them within a run.
    Sorting the line right-to-left turns 1500 into 0051 unless each token is
    reversed back."""
    text = all_text(process_pdf_digital(fixture_bytes))
    assert "1500" in text
    assert "0051" not in text, REJECT["0051"]


def test_latin_words_are_not_reversed(fixture_bytes):
    text = all_text(process_pdf_digital(fixture_bytes))
    assert "SAR" in text
    assert "RAS" not in text, REJECT["RAS"]


def test_mixed_line_keeps_its_word_order(fixture_bytes):
    """Reversing the whole "1500 SAR" island gets the characters right and the
    words backwards. Tokens must be reversed individually."""
    text = all_text(process_pdf_digital(fixture_bytes))
    assert EXPECT_MIXED_LINE in text
    assert "SAR 1500" not in text, REJECT["SAR 1500"]


def test_token_with_inner_punctuation_survives(fixture_bytes):
    """"HR-2026/14" is one LTR token: the hyphen and slash are interior to it and
    must not split it into separately-reversed pieces."""
    assert EXPECT_REFERENCE in all_text(process_pdf_digital(fixture_bytes))


def test_arabic_body_text_reads_forwards(fixture_bytes):
    assert EXPECT_BODY in all_text(process_pdf_digital(fixture_bytes))


# ── Tables ───────────────────────────────────────────────────────────────────


def test_table_is_emitted(fixture_bytes):
    xml = document_xml(process_pdf_digital(fixture_bytes))
    assert xml.count("<w:tbl>") == 1


def test_table_cells_read_forwards(fixture_bytes):
    """The table finder returns cell text as the PDF paints it — visual order —
    so cells have to be rebuilt from their own glyphs."""
    rows = table_rows(process_pdf_digital(fixture_bytes))
    assert rows, "no table rows in the output"
    assert rows[0] == EXPECT_TABLE_HEADER
    assert "ةجردلا" not in "".join(rows[0]), REJECT["ةجردلا"]


def test_table_keeps_the_sources_column_order(fixture_bytes):
    """Column 0 is the RIGHTMOST cell in the source; w:bidiVisual is what makes
    Word lay that out right-to-left rather than mirroring it.

    Rows 2 and 3 are asserted exactly. Row 1 is checked structurally because its
    first cell contains a ligature this font mis-maps — see
    test_known_ligature_defect_is_still_present, which pins that separately.
    """
    rows = table_rows(process_pdf_digital(fixture_bytes))
    assert rows[2:4] == EXPECT_TABLE_ROWS[1:]
    assert rows[1][1:] == ["2500", "SAR"], rows[1]
    assert "bidiVisual" in document_xml(process_pdf_digital(fixture_bytes))


def test_known_ligature_defect_is_still_present(fixture_bytes):
    """A pinned KNOWN FAILURE, not a passing behaviour.

    NotoNaskhArabic's ToUnicode map sends its lam-alef-hamza ligature to U+01C2, a
    Latin click consonant, so `الأولى` extracts as `اǂولى`. Every extractor
    produces the same garbage; it is not recoverable without repairing the font's
    cmap, and guessing the intended letter is exactly what the product must not do.

    Triage routes documents containing it to Gemini (see test_triage), so users
    never receive it. This test exists so that if the defect is ever fixed — a
    PyMuPDF change, a different mapping — we find out here rather than discovering
    that triage is now sending clean documents to OCR for no reason.
    """
    rows = table_rows(process_pdf_digital(fixture_bytes))
    assert "\u01c2" in rows[1][0], (
        f"the ligature defect appears to be gone ({rows[1][0]!r}); "
        "re-check whether triage's broken-ToUnicode rule still earns its keep"
    )


def test_table_rows_do_not_bleed_into_each_other(fixture_bytes):
    """Containment is tested on the glyph's centre; using its baseline (the box's
    bottom edge) pulls the row above into every cell."""
    rows = table_rows(process_pdf_digital(fixture_bytes))
    for row in rows[1:4]:
        assert not any(h in row[0] for h in EXPECT_TABLE_HEADER), row


# ── Structure and page setup ─────────────────────────────────────────────────


def test_headings_are_detected(fixture_bytes):
    """The fixture's headings are an accent colour at close to body size, which a
    size-only rule misses entirely."""
    xml = document_xml(process_pdf_digital(fixture_bytes))
    assert xml.count("Heading1") + xml.count("Heading2") >= 2


def test_page_geometry_is_carried(fixture_bytes):
    xml = document_xml(process_pdf_digital(fixture_bytes))
    assert "<w:pgMar" in xml
    assert "<w:pgBorders" in xml, "the fixture's page frame was not detected"


def test_printed_page_number_becomes_real_numbering(fixture_bytes):
    """The printed number never becomes body text; it sets a PAGE field instead."""
    docx = process_pdf_digital(fixture_bytes)
    assert "<w:pgNumType" in document_xml(docx)
    names = zipfile.ZipFile(io.BytesIO(docx)).namelist()
    assert any("footer" in n for n in names)


# ── Styles ───────────────────────────────────────────────────────────────────


def test_source_style_preserves_colour_and_size(fixture_bytes):
    xml = document_xml(process_pdf_digital(fixture_bytes, style=STYLE_SOURCE))
    colours = set(re.findall(r'<w:color w:val="([0-9A-F]{6})"', xml))
    sizes = {int(v) / 2 for v in re.findall(r'<w:sz w:val="(\d+)"', xml)}
    assert len(colours) >= 2, f"source styling lost the accent colour: {colours}"
    assert len(sizes) >= 2, f"source styling flattened every size: {sizes}"


def test_uniform_style_flattens_appearance(fixture_bytes):
    """The alternative users can pick: one font, one size, no colour — matching
    what the Gemini path produces."""
    xml = document_xml(process_pdf_digital(fixture_bytes, style=STYLE_UNIFORM))
    assert not re.findall(r'<w:color w:val="([0-9A-F]{6})"', xml)
    sizes = {int(v) / 2 for v in re.findall(r'<w:sz w:val="(\d+)"', xml)}
    assert len(sizes) == 1, f"uniform styling kept more than one size: {sizes}"


def test_both_styles_carry_the_same_text(fixture_bytes):
    """Styling changes appearance, never content."""
    source = all_text(process_pdf_digital(fixture_bytes, style=STYLE_SOURCE))
    uniform = all_text(process_pdf_digital(fixture_bytes, style=STYLE_UNIFORM))
    assert EXPECT_MIXED_LINE in source and EXPECT_MIXED_LINE in uniform


# ── Robustness ───────────────────────────────────────────────────────────────


def test_alignment_is_always_logical(fixture_bytes):
    xml = document_xml(process_pdf_digital(fixture_bytes))
    values = set(re.findall(r'<w:jc w:val="(\w+)"', xml))
    assert "right" not in values and "left" not in values, values


def test_max_pages_caps_the_conversion(fixture_bytes):
    """What the anonymous trial relies on."""
    one = process_pdf_digital(fixture_bytes, max_pages=1)
    assert document_xml(one).count('w:type="page"') == 0  # no page break => one page


def test_glyph_without_a_character_does_not_crash():
    """Some producers emit a glyph carrying no character at all; every classifier
    downstream calls ord() on it. Three documents in the real corpus did this."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "نص عربي")
    data = doc.tobytes()
    doc.close()
    assert process_pdf_digital(data)  # must not raise


def test_empty_pdf_produces_a_document_not_an_exception():
    doc = fitz.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    assert process_pdf_digital(data)


# ── Background fills ─────────────────────────────────────────────────────────


def test_title_band_fill_is_carried(fixture_bytes):
    """A coloured band behind a heading is content, not decoration.

    The text painted on such a band is routinely WHITE, so dropping the fill does
    not merely lose a colour — it leaves white text on a white page and the
    heading disappears entirely. This was found on a real user document whose
    brown header vanished from the conversion.
    """
    xml = document_xml(process_pdf_digital(fixture_bytes, style=STYLE_SOURCE))
    fills = set(re.findall(r'<w:shd[^>]*w:fill="([0-9A-F]{6})"', xml))
    assert EXPECT_BAND_FILL in fills, f"the title band's fill was lost: {fills}"


def test_text_on_the_band_survives_with_it(fixture_bytes):
    text = all_text(process_pdf_digital(fixture_bytes, style=STYLE_SOURCE))
    assert EXPECT_BAND_TITLE in text


def test_uniform_style_drops_shading_without_hiding_text(fixture_bytes):
    """Uniform output has no fills — and must therefore also drop the white text
    colour, or the heading would be invisible for the opposite reason."""
    xml = document_xml(process_pdf_digital(fixture_bytes, style=STYLE_UNIFORM))
    assert not re.findall(r"<w:shd[^>]*w:fill=", xml)
    assert "FFFFFF" not in re.findall(r'<w:color w:val="([0-9A-F]{6})"', xml)
    assert EXPECT_BAND_TITLE in all_text(process_pdf_digital(fixture_bytes,
                                                             style=STYLE_UNIFORM))


def test_page_sized_fill_is_not_treated_as_shading():
    """A full-page background would otherwise shade every paragraph in the
    document."""
    from tests.fixtures import arabic_page

    def full_background(page, pymupdf):
        page.draw_rect(page.rect, color=None, fill=(0.9, 0.9, 0.5))

    data = arabic_page("<p>نص عربي على خلفية كاملة</p>", draw=full_background)
    xml = document_xml(process_pdf_digital(data))
    assert not re.findall(r"<w:shd[^>]*w:fill=", xml)


# ── Alignment ────────────────────────────────────────────────────────────────


def test_title_centred_on_the_page_is_detected_despite_an_offset_column():
    """Centring is judged against the page as well as the text column.

    A document whose tables reach further right than its body text has an
    ASYMMETRIC column, and its midpoint is then not the page's. A real document
    centred its title at x=420.95 on an 842pt page — dead centre — while the
    column's midpoint sat at 467, so testing against the column alone called it
    92pt off and left the title right-aligned.
    """
    from tests.fixtures import arabic_page

    # The title is centred; the body below it is pushed right, so the text column
    # it would otherwise be measured against is not centred on the page.
    data = arabic_page(
        '<p style="text-align:center">عنوان الصفحة</p>'
        + '<p style="margin-right:0;margin-left:35%">'
        + ("نص عربي للمحتوى الأساسي في هذه الصفحة. " * 12)
        + "</p>",
        width=842, height=595,
    )
    xml = document_xml(process_pdf_digital(data))
    assert '<w:jc w:val="center"/>' in xml


def test_page_sized_sparse_grid_is_not_treated_as_a_table():
    """A graphical page produces ruling lines the table finder reads as a grid.

    Accepting it is far worse than missing a real table: every line on the page
    becomes a cell, so paragraphs, headings and their alignment are gone. A real
    workbook cover lost all of its centring this way — 12 pages, each one "table".
    """
    from tests.fixtures import arabic_page

    def grid(page, pymupdf):
        for i in range(6):
            y = 40 + i * 130
            page.draw_line(pymupdf.Point(40, y), pymupdf.Point(555, y))
        for i in range(5):
            x = 40 + i * 128
            page.draw_line(pymupdf.Point(x, 40), pymupdf.Point(x, 690))

    data = arabic_page('<p style="text-align:center">عنوان الدفتر</p>', draw=grid)
    xml = document_xml(process_pdf_digital(data))
    assert "<w:tbl>" not in xml, "a decorative grid was rendered as a table"
    assert "عنوان" in all_text(process_pdf_digital(data))


def test_a_real_small_table_is_still_detected(fixture_bytes):
    """The guard above must not take genuine tables with it. On the real corpus a
    true 3x3 table was SPARSER than the decorative grids (11% vs 14% filled) — it
    is the page coverage that separates them, which is why both conditions are
    required."""
    assert document_xml(process_pdf_digital(fixture_bytes)).count("<w:tbl>") == 1


# ── Paragraphs and titles ────────────────────────────────────────────────────


def test_paragraphs_split_at_tight_spacing():
    """Paragraph breaks are measured against the DOMINANT line spacing.

    Real documents set paragraph gaps at 1.2-1.3x their line spacing, not the 1.5x
    that reads as obvious. A document whose lines sit 33.5pt apart and whose
    paragraphs sit 39.5pt apart had all four of its paragraphs merged into one.
    """
    from tests.fixtures import arabic_page

    body = "هذه فقرة عربية كاملة تحتوي على عدة كلمات لاختبار الفصل بين الفقرات. "
    data = arabic_page("".join(
        f'<p style="margin-bottom:6px">{body * 2}</p>' for _ in range(4)
    ))
    xml = document_xml(process_pdf_digital(data))
    # Four paragraphs, not one run-on block.
    assert xml.count("<w:p>") >= 4, "paragraphs were merged into one"


def test_centred_line_slightly_larger_than_body_is_a_heading():
    """Size alone misses real section titles.

    One document set its titles at 18pt against a 16pt body — 1.12x, under any
    sane size threshold — but centred them. A centred line cannot be a justified
    body line, because centring requires an inset on BOTH sides, so the
    combination is safe to treat as a title.
    """
    from tests.fixtures import arabic_page

    body = "نص عربي عادي يملأ عرض العمود بالكامل لكي يكون سطرا من سطور المتن. "
    data = arabic_page(
        '<p style="text-align:center;font-size:18px">مقدمة:</p>'
        f'<p style="font-size:16px">{body * 4}</p>'
    )
    xml = document_xml(process_pdf_digital(data))
    assert "Heading1" in xml or "Heading2" in xml, "the centred title was read as body text"


def test_body_text_is_not_turned_into_headings():
    """The guard on the rule above: ordinary justified prose must stay prose."""
    from tests.fixtures import arabic_page

    body = "نص عربي عادي يملأ عرض العمود بالكامل لكي يكون سطرا من سطور المتن. "
    data = arabic_page("".join(
        f'<p style="text-align:justify">{body * 3}</p>' for _ in range(3)
    ))
    xml = document_xml(process_pdf_digital(data))
    assert "Heading1" not in xml and "Heading2" not in xml
