"""The style-carrying DOCX builder.

Word lays Arabic out from the COMPLEX-SCRIPT half of every property — w:cs,
w:szCs, w:bCs — so a run styled only on the Latin side renders in Word's default
font at Word's default size while looking correct in the XML. These tests assert
on both halves for that reason.
"""

import io
import re
import zipfile

from app.ocr.styled_builder import (
    Block,
    PageBorder,
    PageSetup,
    Run,
    build_styled_docx,
    map_font,
)

ARABIC = "قال المؤلف إن هذه المسألة مشهورة"


def build(pages, setup=None) -> zipfile.ZipFile:
    buf = io.BytesIO()
    build_styled_docx(pages, buf, setup)
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


def document(z) -> str:
    return z.read("word/document.xml").decode()


# ── Run properties ───────────────────────────────────────────────────────────


def test_font_is_written_to_the_complex_script_side():
    z = build([[Block("para", runs=[Run(ARABIC, font="Traditional Arabic")])]])
    xml = document(z)
    assert 'w:cs="Traditional Arabic"' in xml, "Arabic would fall back to Word's default"
    assert 'w:ascii="Traditional Arabic"' in xml


def test_size_is_written_to_the_complex_script_side():
    z = build([[Block("para", runs=[Run(ARABIC, size=18.0)])]])
    xml = document(z)
    assert '<w:sz w:val="36"/>' in xml      # half-points
    assert '<w:szCs w:val="36"/>' in xml


def test_bold_is_written_to_the_complex_script_side():
    z = build([[Block("para", runs=[Run(ARABIC, bold=True)])]])
    xml = document(z)
    assert "<w:b/>" in xml and "<w:bCs/>" in xml, "w:b alone leaves Arabic un-bolded"


def test_colour_and_underline_are_emitted():
    z = build([[Block("para", runs=[Run(ARABIC, color=0xC00000, underline=True)])]])
    xml = document(z)
    assert '<w:color w:val="C00000"/>' in xml
    assert '<w:u w:val="single"/>' in xml


def test_arabic_runs_are_marked_rtl():
    z = build([[Block("para", runs=[Run(ARABIC)])]])
    assert "<w:rtl/>" in document(z)


def test_latin_inside_an_arabic_line_is_not_marked_rtl():
    """Each run splits at script boundaries so a Latin word keeps its own
    direction inside an Arabic paragraph."""
    z = build([[Block("para", runs=[Run(f"{ARABIC} Smith 1998")])]])
    xml = document(z)
    runs = re.findall(r"<w:r>.*?</w:r>", xml, re.S)
    latin = [r for r in runs if "Smith" in r]
    assert latin and all("<w:rtl/>" not in r for r in latin)


# ── Paragraph and section ────────────────────────────────────────────────────


def test_alignment_is_logical_never_physical():
    """Word for Mac resolves "right" as the logical END of the line, which in an
    RTL paragraph is the visually left margin."""
    z = build([[Block("para", runs=[Run(ARABIC)]),
                Block("para", runs=[Run("An English paragraph")])]])
    values = set(re.findall(r'<w:jc w:val="(\w+)"', document(z)))
    assert values and "right" not in values and "left" not in values, values


def test_explicit_alignment_is_honoured():
    z = build([[Block("para", runs=[Run(ARABIC)], align="center")]])
    assert '<w:jc w:val="center"/>' in document(z)


def test_page_margins_are_written_in_twips():
    setup = PageSetup(margin_top_pt=36, margin_bottom_pt=36,
                      margin_left_pt=72, margin_right_pt=72)
    xml = document(build([[Block("para", runs=[Run(ARABIC)])]], setup))
    assert 'w:top="720"' in xml and 'w:left="1440"' in xml


def test_page_border_is_offset_from_the_paper_edge():
    """offsetFrom="page" is the difference between a frame at the paper edge and
    one floating inside a wide margin."""
    setup = PageSetup(border=PageBorder(style="thickThinSmallGap",
                                        size_eighths=36, space_pt=24))
    xml = document(build([[Block("para", runs=[Run(ARABIC)])]], setup))
    assert '<w:pgBorders w:offsetFrom="page">' in xml
    assert xml.count('w:val="thickThinSmallGap"') == 4, "a frame has four sides"


def test_printed_page_number_becomes_a_real_field():
    setup = PageSetup(page_number_align="center", page_number_start="5")
    z = build([[Block("para", runs=[Run(ARABIC)])]], setup)
    assert '<w:pgNumType w:start="5"/>' in document(z)
    footer = next(n for n in z.namelist() if "footer" in n)
    assert "PAGE" in z.read(footer).decode(), "a static number would not renumber"


def test_rtl_table_is_marked_bidi_visual():
    """Without it Word draws column 1 on the LEFT, mirroring the source table."""
    rows = [[[Run("الدرجة")], [Run("البدل")]], [[Run("الأولى")], [Run("2500")]]]
    xml = document(build([[Block("table", rows=rows, has_header_row=True)]]))
    assert "bidiVisual" in xml


# ── Robustness ───────────────────────────────────────────────────────────────


def test_control_characters_are_stripped_before_xml():
    """A font subset lacking a glyph yields NULs; lxml rejects them, so one bad
    glyph would otherwise fail the whole document."""
    z = build([[Block("para", runs=[Run("نص\x00\x01عربي")])]])
    assert "نص" in document(z)


def test_empty_blocks_do_not_produce_empty_paragraphs():
    z = build([[Block("para", runs=[Run("   ")]), Block("para", runs=[Run(ARABIC)])]])
    assert document(z).count("<w:p>") < 4


def test_pages_are_separated_by_page_breaks():
    z = build([[Block("para", runs=[Run(ARABIC)])],
               [Block("para", runs=[Run(ARABIC)])]])
    assert document(z).count('w:type="page"') == 1


# ── Font mapping ─────────────────────────────────────────────────────────────


def test_subset_prefix_and_style_suffix_are_stripped():
    """Weight lives in w:b, not in the family name; Word cannot resolve
    "ABCDEF+Arial-BoldMT"."""
    assert map_font("ABCDEF+Arial-BoldMT") == "Arial"
    assert map_font("TimesNewRomanPSMT") == "TimesNewRoman"
    assert map_font("TraditionalArabic") == "TraditionalArabic"


def test_unknown_font_falls_back_rather_than_guessing():
    assert map_font("", fallback="Arial") == "Arial"
