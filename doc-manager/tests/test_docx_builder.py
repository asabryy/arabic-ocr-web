"""Structured DOCX assembly, asserted against the real OOXML inside the .docx zip.

These tests deliberately unzip the generated file and read ``word/document.xml``
rather than trusting ``python-docx``'s object model: the defect they exist to stop
(``run.font.name`` setting only the Latin font, so Arabic silently rendered in Word's
default) was invisible from the Python side and only visible in the XML.
"""

import io
import re
import zipfile

import pytest
from lxml import etree

from app.core.config import settings
from app.ocr import pipeline
from tests.conftest import make_pdf

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ARABIC_PAGE = """[[header: مجلة الدراسات الإسلامية]]
# الباب الأول في الطهارة

قال المؤلف رحمه الله إن هذه المسألة قد اختلف فيها أهل العلم على قولين مشهورين.

وذهب الجمهور إلى القول الثاني.

## جدول المقارنة

| السنة | الحدث | Reference |
| --- | --- | --- |
| ١٤٢٠ | افتتاح | Smith 1999 |
| ١٤٢١ | إغلاق | Jones 2000 |

- البند الأول
- البند الثاني

1. الوجه الأول
2. الوجه الثاني

[[footnotes]]
انظر: ابن ⟦?⟧ في كتابه المطبوع.
[[page: ٣٧]]
"""

LATIN_PAGE = """This is an English paragraph and it must not be forced right-to-left.

نص عربي على الصفحة الثانية يذكر اسم Smith ورقم 1998 داخل الفقرة.
[[header: مجلة الدراسات الإسلامية]]
[[page: ٣٨]]
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def build(pages: list[str]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    pipeline.build_docx(pages, buf)
    data = buf.getvalue()
    assert data[:2] == b"PK", "not a zip container"
    return zipfile.ZipFile(io.BytesIO(data))


def part(z: zipfile.ZipFile, name: str = "word/document.xml") -> str:
    return z.read(name).decode("utf-8")


def root(z: zipfile.ZipFile, name: str = "word/document.xml"):
    return etree.fromstring(z.read(name))


def body_paragraphs(doc_root) -> list:
    """Top-level <w:p> of the body — excludes paragraphs nested inside table cells."""
    body = doc_root.find(f"{W}body")
    return [child for child in body if child.tag == f"{W}p"]


def text_of(element) -> str:
    return "".join(t.text or "" for t in element.iter(f"{W}t"))


def runs_of(element) -> list:
    return list(element.iter(f"{W}r"))


def rpr(run):
    return run.find(f"{W}rPr")


def has(run, tag: str) -> bool:
    return rpr(run) is not None and rpr(run).find(f"{W}{tag}") is not None


def pstyle(paragraph) -> str | None:
    pPr = paragraph.find(f"{W}pPr")
    if pPr is None:
        return None
    style = pPr.find(f"{W}pStyle")
    return None if style is None else style.get(f"{W}val")


def bidi_val(paragraph) -> str | None:
    pPr = paragraph.find(f"{W}pPr")
    if pPr is None:
        return None
    bidi = pPr.find(f"{W}bidi")
    return None if bidi is None else bidi.get(f"{W}val")


def jc_val(paragraph) -> str | None:
    pPr = paragraph.find(f"{W}pPr")
    if pPr is None:
        return None
    jc = pPr.find(f"{W}jc")
    return None if jc is None else jc.get(f"{W}val")


def find_paragraph(paragraphs, needle: str):
    for p in paragraphs:
        if needle in text_of(p):
            return p
    raise AssertionError(f"no paragraph containing {needle!r}")


# ── complex-script attributes (defect 1) ──────────────────────────────────────

def test_every_run_carries_complex_script_font_and_size():
    """w:cs / w:szCs on every run — Word lays Arabic out from these, not w:ascii/w:sz."""
    z = build([ARABIC_PAGE, LATIN_PAGE])
    doc = root(z)
    runs = [r for r in doc.iter(f"{W}r") if text_of(r)]
    assert runs, "document has no text runs"
    for run in runs:
        fonts = rpr(run).find(f"{W}rFonts")
        assert fonts is not None, etree.tostring(run)
        assert fonts.get(f"{W}cs") == settings.DOCX_FONT
        assert fonts.get(f"{W}ascii") == settings.DOCX_FONT
        assert fonts.get(f"{W}hAnsi") == settings.DOCX_FONT
        sz = rpr(run).find(f"{W}sz")
        szCs = rpr(run).find(f"{W}szCs")
        assert sz is not None and szCs is not None, etree.tostring(run)
        assert sz.get(f"{W}val") == szCs.get(f"{W}val")

    xml = part(z)
    assert xml.count('w:cs="') >= len(runs)
    assert xml.count("<w:szCs ") >= len(runs)
    assert "<w:rtl/>" in xml


def test_body_text_size_is_the_configured_point_size():
    z = build(["فقرة عربية بسيطة للاختبار."])
    run = runs_of(body_paragraphs(root(z))[0])[0]
    half_points = str(int(settings.DOCX_FONT_SIZE_PT * 2))
    assert rpr(run).find(f"{W}sz").get(f"{W}val") == half_points
    assert rpr(run).find(f"{W}szCs").get(f"{W}val") == half_points


def test_arabic_runs_are_marked_rtl():
    z = build(["قال المؤلف إن هذه المسألة مشهورة."])
    para = body_paragraphs(root(z))[0]
    assert bidi_val(para) == "1"
    assert jc_val(para) == "right"
    assert all(has(r, "rtl") for r in runs_of(para))


# ── paragraph direction (defect 5) ────────────────────────────────────────────

def test_latin_paragraph_is_not_forced_rtl():
    z = build([LATIN_PAGE])
    para = find_paragraph(body_paragraphs(root(z)), "English paragraph")
    assert bidi_val(para) == "0", "Latin paragraph was given an RTL base direction"
    assert jc_val(para) == "left", "Latin paragraph was right-aligned"
    assert not any(has(r, "rtl") for r in runs_of(para))


def test_mixed_paragraph_splits_runs_at_script_boundaries():
    """An Arabic paragraph quoting a Latin name: the Latin run must not carry w:rtl."""
    z = build(["نص عربي يذكر اسم Smith ورقم 1998 داخل الفقرة."])
    para = body_paragraphs(root(z))[0]
    assert bidi_val(para) == "1"
    runs = runs_of(para)
    assert len(runs) >= 3, "mixed-script paragraph was emitted as one undifferentiated run"
    latin = [r for r in runs if "Smith" in text_of(r)]
    assert latin and not any(has(r, "rtl") for r in latin)
    arabic = [r for r in runs if "عربي" in text_of(r)]
    assert arabic and all(has(r, "rtl") for r in arabic)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("قال المؤلف", True),
        ("Hello world", False),
        ("Le français et l'anglais", False),
        ("١٤٢٠", True),          # neutral-only → document default
        ("1999", True),          # neutral-only → document default
        ("", True),
        ("نص Smith", True),      # Arabic majority
        ("Smith and Jones قال", False),
    ],
)
def test_direction_detection(text, expected):
    assert pipeline.is_rtl_text(text, default=True) is expected


def test_direction_detection_respects_default_for_neutral_text():
    assert pipeline.is_rtl_text("123", default=False) is False


# ── paragraph reflow (defect 2) ───────────────────────────────────────────────

def test_blank_line_separated_paragraphs_are_not_split_per_line():
    """Two logical paragraphs stay two <w:p>, whatever the model's own line wrapping."""
    page = "الفقرة الأولى كاملة في سطر واحد.\n\nالفقرة الثانية كاملة في سطر واحد."
    paragraphs = [p for p in body_paragraphs(root(build([page]))) if text_of(p).strip()]
    assert len(paragraphs) == 2


def test_hard_line_breaks_inside_a_block_stay_in_one_paragraph():
    """Verse and addresses keep their line breaks — as <w:br/>, inside one paragraph."""
    page = "ألا ليت الشباب يعود يوما\nفأخبره بما فعل المشيب"
    paragraphs = [p for p in body_paragraphs(root(build([page]))) if text_of(p).strip()]
    assert len(paragraphs) == 1
    brs = [b for b in paragraphs[0].iter(f"{W}br") if b.get(f"{W}type") is None]
    assert len(brs) == 1


def test_no_empty_paragraph_per_source_blank_line():
    page = "فقرة.\n\n\n\nفقرة أخرى."
    paragraphs = body_paragraphs(root(build([page])))
    assert len([p for p in paragraphs if not text_of(p).strip()]) == 0


# ── tables (defect 3) ─────────────────────────────────────────────────────────

def test_markdown_table_becomes_a_real_word_table():
    z = build([ARABIC_PAGE])
    doc = root(z)
    tables = list(doc.iter(f"{W}tbl"))
    assert len(tables) == 1, "the pipe table did not become a <w:tbl>"

    rows = list(tables[0].iter(f"{W}tr"))
    assert len(rows) == 3, "the |---| separator row was kept as data"
    cells = [text_of(c) for c in rows[0].iter(f"{W}tc")]
    assert cells == ["السنة", "الحدث", "Reference"]
    assert [text_of(c) for c in rows[1].iter(f"{W}tc")] == ["١٤٢٠", "افتتاح", "Smith 1999"]


def test_rtl_table_sets_bidi_visual_so_columns_are_not_mirrored():
    z = build([ARABIC_PAGE])
    tbl = next(root(z).iter(f"{W}tbl"))
    tblPr = tbl.find(f"{W}tblPr")
    assert tblPr.find(f"{W}bidiVisual") is not None


def test_table_header_row_is_bold_on_both_scripts():
    z = build([ARABIC_PAGE])
    row = next(next(root(z).iter(f"{W}tbl")).iter(f"{W}tr"))
    runs = [r for r in row.iter(f"{W}r") if text_of(r)]
    assert runs and all(has(r, "b") and has(r, "bCs") for r in runs)


def test_latin_table_cell_keeps_ltr_direction():
    z = build([ARABIC_PAGE])
    tbl = next(root(z).iter(f"{W}tbl"))
    cell = [c for c in tbl.iter(f"{W}tc") if text_of(c) == "Smith 1999"][0]
    para = cell.find(f"{W}p")
    assert bidi_val(para) == "0"


def test_no_literal_pipe_characters_survive_in_the_text():
    z = build([ARABIC_PAGE])
    visible = "".join(t.text or "" for t in root(z).iter(f"{W}t"))
    assert "|" not in visible
    assert "---" not in visible


def test_table_without_header_separator_has_no_bold_row():
    page = "| أ | ب |\n| ج | د |"
    z = build([page])
    rows = list(next(root(z).iter(f"{W}tbl")).iter(f"{W}tr"))
    assert len(rows) == 2
    assert not any(has(r, "b") for r in rows[0].iter(f"{W}r"))


# ── headings and lists (defect 4) ─────────────────────────────────────────────

def test_headings_use_word_heading_styles():
    z = build([ARABIC_PAGE])
    paragraphs = body_paragraphs(root(z))
    h1 = find_paragraph(paragraphs, "الباب الأول")
    h2 = find_paragraph(paragraphs, "جدول المقارنة")
    assert pstyle(h1) == "Heading1"
    assert pstyle(h2) == "Heading2"
    assert "#" not in text_of(h1)
    # Word's Heading styles set only the Latin theme font, so the complex-script side
    # has to be written explicitly or Arabic headings fall back to the default face.
    assert all(rpr(r).find(f"{W}rFonts").get(f"{W}cs") == settings.DOCX_FONT
               for r in runs_of(h1))
    assert all(has(r, "bCs") for r in runs_of(h1))


def test_bulleted_items_become_list_paragraphs():
    z = build([ARABIC_PAGE])
    paragraphs = body_paragraphs(root(z))
    item = find_paragraph(paragraphs, "البند الأول")
    assert pstyle(item) == "ListBullet"
    assert not text_of(item).startswith("-")


def test_numbered_items_keep_the_printed_numeral():
    """Word's own numbering would re-render ١ as 1 — the digit script must survive."""
    page = "١. الوجه الأول\n٢. الوجه الثاني"
    paragraphs = body_paragraphs(root(build([page])))
    items = [p for p in paragraphs if pstyle(p) == "ListParagraph"]
    assert len(items) == 2
    assert text_of(items[0]).startswith("١.")


def test_a_year_at_the_start_of_a_paragraph_is_not_a_list_item():
    page = "1998 كان عاما مهما في تاريخ هذه المدينة."
    para = body_paragraphs(root(build([page])))[0]
    assert pstyle(para) is None


# ── page size, page breaks, running heads (defect 4) ──────────────────────────

def test_page_size_is_a4():
    z = build([ARABIC_PAGE])
    sectPr = next(root(z).iter(f"{W}sectPr"))
    pgSz = sectPr.find(f"{W}pgSz")
    assert pgSz.get(f"{W}w") == "11906"
    assert pgSz.get(f"{W}h") == "16838"
    assert "12240" not in part(z), "US Letter page size leaked through"


def test_page_breaks_are_real_not_a_text_marker():
    z = build([ARABIC_PAGE, LATIN_PAGE, "صفحة ثالثة."])
    xml = part(z)
    assert xml.count('<w:br w:type="page"/>') == 2, "expected one break between pages"
    visible = "".join(t.text or "" for t in root(z).iter(f"{W}t"))
    assert "-- Page" not in visible
    assert "Page 2" not in visible


def test_single_page_document_has_no_page_break():
    assert '<w:br w:type="page"/>' not in part(build([ARABIC_PAGE]))


def test_section_is_right_to_left_for_an_arabic_document():
    sectPr = next(root(build([ARABIC_PAGE])).iter(f"{W}sectPr"))
    assert sectPr.find(f"{W}bidi") is not None


def test_latin_only_document_is_not_forced_rtl():
    z = build(["A wholly English document.\n\nWith a second paragraph."])
    sectPr = next(root(z).iter(f"{W}sectPr"))
    assert sectPr.find(f"{W}bidi") is None
    assert all(bidi_val(p) == "0" for p in body_paragraphs(root(z)) if text_of(p))


def test_running_heads_leave_the_body_and_become_a_word_header():
    z = build([ARABIC_PAGE, LATIN_PAGE])
    visible = "".join(t.text or "" for t in root(z).iter(f"{W}t"))
    assert "[[" not in visible and "]]" not in visible
    assert "مجلة الدراسات الإسلامية" not in visible, "running head left in the body"
    assert "word/header1.xml" in z.namelist()
    assert "مجلة الدراسات الإسلامية" in part(z, "word/header1.xml")


def test_printed_page_number_sets_the_field_start_not_body_text():
    z = build([ARABIC_PAGE, LATIN_PAGE])
    sectPr = next(root(z).iter(f"{W}sectPr"))
    pgNumType = sectPr.find(f"{W}pgNumType")
    assert pgNumType is not None and pgNumType.get(f"{W}start") == "37"
    footer = part(z, "word/footer1.xml")
    assert "PAGE" in footer, "expected a real PAGE field rather than a transcribed number"


def test_explicit_footer_marker_wins_over_the_page_field():
    z = build(["نص.\n[[footer: دار النشر]]"])
    footer = part(z, "word/footer1.xml")
    assert "دار النشر" in footer
    assert "fldSimple" not in footer


def test_no_header_part_when_the_page_has_no_running_head():
    z = build(["فقرة عادية بلا ترويسة."])
    assert "word/header1.xml" not in z.namelist()
    assert "word/footer1.xml" not in z.namelist()


def test_footnote_block_is_separated_and_set_smaller():
    z = build([ARABIC_PAGE])
    doc = root(z)
    note = find_paragraph(body_paragraphs(doc), "في كتابه المطبوع")
    half = str(int(settings.DOCX_FOOTNOTE_SIZE_PT * 2))
    assert rpr(runs_of(note)[0]).find(f"{W}szCs").get(f"{W}val") == half
    assert any(p.find(f"{W}pPr") is not None and p.find(f"{W}pPr").find(f"{W}pBdr") is not None
               for p in body_paragraphs(doc)), "no rule above the footnotes"


def test_illegible_marker_is_preserved_and_highlighted():
    z = build([ARABIC_PAGE])
    marked = [r for r in root(z).iter(f"{W}r") if text_of(r) == pipeline.ILLEGIBLE]
    assert marked, "the ⟦?⟧ gap marker was dropped"
    assert all(rpr(r).find(f"{W}highlight") is not None for r in marked)


def test_markdown_bold_does_not_reach_the_reader_as_asterisks():
    z = build(["هذا **نص عريض** في فقرة."])
    para = body_paragraphs(root(z))[0]
    assert "**" not in text_of(para)
    bold = [r for r in runs_of(para) if has(r, "b")]
    assert bold and text_of(bold[0]) == "نص عريض"


# ── parser unit tests ─────────────────────────────────────────────────────────

def test_parse_page_lifts_markers_out_of_the_blocks():
    page = pipeline._parse_page(ARABIC_PAGE)
    assert page.header == "مجلة الدراسات الإسلامية"
    assert page.page_label == "٣٧"
    kinds = [b.kind for b in page.blocks]
    assert kinds.count("table") == 1
    assert kinds.count("heading") == 2
    assert kinds.count("bullet") == 2
    assert kinds.count("ordered") == 2
    assert not any("[[" in line for b in page.blocks for line in b.lines)


def test_parse_page_tolerates_code_fences_and_ragged_tables():
    page = pipeline._parse_page("```\n| أ | ب | ج |\n| د |\n```")
    table = [b for b in page.blocks if b.kind == "table"][0]
    assert table.rows == [["أ", "ب", "ج"], ["د", "", ""]]


def test_parse_page_handles_empty_and_whitespace_input():
    assert pipeline._parse_page("").blocks == []
    assert pipeline._parse_page("   \n\n  ").blocks == []


def test_empty_pages_still_produce_a_valid_document():
    z = build(["", "", ""])
    assert part(z).count('<w:br w:type="page"/>') == 2


def test_windows_line_endings_are_normalised():
    page = "فقرة أولى.\r\n\r\nفقرة ثانية."
    paragraphs = [p for p in body_paragraphs(root(build([page]))) if text_of(p).strip()]
    assert len(paragraphs) == 2
    assert "\r" not in "".join(text_of(p) for p in paragraphs)


# ── prompt contract ───────────────────────────────────────────────────────────

def test_prompt_forbids_guessing_and_asks_for_structure():
    prompt = pipeline.OCR_PROMPT
    assert "best guess" not in prompt.lower()
    assert "NEVER guess" in prompt
    assert pipeline.ILLEGIBLE in prompt
    assert "preserve the original line breaks" not in prompt.lower()
    for token in ("[[header:", "[[footer:", "[[page:", "[[footnotes]]", "# ", "## ", "| cell | cell |"):
        assert token in prompt, token
    assert "tashkeel" in prompt.lower()
    assert "Arabic-Indic" in prompt


# ── public surface ────────────────────────────────────────────────────────────

def test_process_pdf_signature_is_unchanged(monkeypatch):
    """The worker and the anonymous trial both call this exact signature."""
    import inspect

    sig = inspect.signature(pipeline.process_pdf)
    assert list(sig.parameters) == ["pdf_bytes", "max_pages", "mode"]
    assert sig.parameters["max_pages"].default is None
    assert sig.parameters["mode"].default == "ocr"


def test_process_pdf_end_to_end_emits_a_structured_document(monkeypatch):
    monkeypatch.setattr(pipeline, "ocr_page", lambda png: ARABIC_PAGE)
    out = pipeline.process_pdf(make_pdf(2), mode="trial")
    assert out[:2] == b"PK"
    xml = zipfile.ZipFile(io.BytesIO(out)).read("word/document.xml").decode()
    assert "<w:tbl>" in xml
    assert '<w:br w:type="page"/>' in xml
    assert 'w:cs="Arial"' in xml
    assert "<w:rtl/>" in xml
    assert re.search(r'<w:pgSz w:w="11906" w:h="16838"/>', xml)
