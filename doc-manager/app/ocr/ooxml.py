"""Low-level OOXML helpers shared by both DOCX builders.

Child order is not optional in OOXML: Word rejects (or silently ignores)
properties written out of schema sequence, which is how ``w:cs`` can "be set" and
do nothing. The sequences below are the schema's, and ``set_child`` is the only
sanctioned way to write one.

Also holds the RTL hardening pass. Two of the layers Word needs cannot be written
through python-docx at all, so they are applied to the saved package.
"""

import io
import re
import zipfile

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PPR_SEQ = (
    "w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
    "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs",
    "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
    "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
    "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
    "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
    "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
    "w:pPrChange",
)
SECTPR_SEQ = (
    "w:footnotePr", "w:endnotePr", "w:type", "w:pgSz", "w:pgMar", "w:paperSrc",
    "w:pgBorders", "w:lnNumType", "w:pgNumType", "w:cols", "w:formProt", "w:vAlign",
    "w:noEndnote", "w:titlePg", "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid",
    "w:printerSettings", "w:sectPrChange",
)
RPR_SEQ = (
    "w:rStyle", "w:rFonts", "w:b", "w:bCs", "w:i", "w:iCs", "w:caps", "w:smallCaps",
    "w:strike", "w:dstrike", "w:outline", "w:shadow", "w:emboss", "w:imprint",
    "w:noProof", "w:snapToGrid", "w:vanish", "w:webHidden", "w:color", "w:spacing",
    "w:w", "w:kern", "w:position", "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect",
    "w:bdr", "w:shd", "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang",
    "w:eastAsianLayout", "w:specVanish", "w:oMath",
)

# A4 in twentieths of a point: 210 x 297 mm.
A4_WIDTH_TWIPS = 11906
A4_HEIGHT_TWIPS = 16838


def set_child(parent, seq: tuple[str, ...], tag: str, **attrs: str):
    """Replace ``tag`` under ``parent``, inserted at its schema-mandated position."""
    parent.remove_all(tag)
    el = OxmlElement(tag)
    for name, value in attrs.items():
        el.set(qn(name), value)
    successors = seq[seq.index(tag) + 1:] if tag in seq else ()
    parent.insert_element_before(el, *successors)
    return el


def half_points(size_pt: float) -> str:
    """Word expresses font size in half-points (``w:sz``/``w:szCs``)."""
    return str(int(round(size_pt * 2)))


def twips(points: float) -> str:
    """Word expresses page geometry in twentieths of a point."""
    return str(int(round(points * 20)))


def add_break(para, kind: str | None = None) -> None:
    br = OxmlElement("w:br")
    if kind:
        br.set(qn("w:type"), kind)
    para.add_run()._r.append(br)


def xml_safe(text: str) -> str:
    """Drop characters XML 1.0 cannot carry.

    A PDF whose font subset lacks a glyph yields NULs and other control codes in
    the extracted text; lxml rejects them, so one bad glyph anywhere would fail the
    whole document. Filtering at the single point where text becomes XML means no
    caller has to remember to.
    """
    return "".join(
        ch for ch in text
        if ch in "\t\n\r"
        or 0x20 <= ord(ch) <= 0xD7FF
        or 0xE000 <= ord(ch) <= 0xFFFD
        or 0x10000 <= ord(ch) <= 0x10FFFF
    )


# ── RTL hardening ────────────────────────────────────────────────────────────

_THEME_FONT_LANG_RE = re.compile(r"<w:themeFontLang\b[^>]*/>")


def harden_rtl(docx_bytes: bytes, bidi_locale: str = "ar-SA") -> bytes:
    """Apply the two RTL layers python-docx cannot reach.

    1. ``w:jc`` becomes ``start``/``end`` rather than ``left``/``right``. Word for
       Mac resolves ``right`` as the LOGICAL end of the line, which in an RTL
       paragraph is the visually left margin — so a document that looks correct on
       Windows is left-aligned on macOS.
    2. ``<w:themeFontLang w:bidi="..."/>`` in settings.xml. python-docx's default
       template sets only ``w:val`` and ``w:eastAsia``; without the ``w:bidi``
       attribute Word left-aligns RTL body text no matter what the paragraphs say.

    Operates on the saved package because neither is expressible through the
    object model. Idempotent: running it twice changes nothing.
    """
    src = zipfile.ZipFile(io.BytesIO(docx_bytes))
    buf = io.BytesIO()
    out = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)

    try:
        for item in src.infolist():
            data = src.read(item.filename)

            if item.filename in ("word/document.xml", "word/footer1.xml",
                                 "word/header1.xml"):
                xml = data.decode("utf-8")
                xml = xml.replace('<w:jc w:val="right"/>', '<w:jc w:val="end"/>')
                xml = xml.replace('<w:jc w:val="left"/>', '<w:jc w:val="start"/>')
                data = xml.encode("utf-8")

            elif item.filename == "word/settings.xml":
                data = _with_bidi_theme_lang(data.decode("utf-8"), bidi_locale).encode("utf-8")

            out.writestr(item, data)
    finally:
        out.close()
        src.close()
    return buf.getvalue()


def _with_bidi_theme_lang(xml: str, locale: str) -> str:
    match = _THEME_FONT_LANG_RE.search(xml)
    if match:
        tag = match.group(0)
        if "w:bidi=" in tag:
            new = re.sub(r'w:bidi="[^"]*"', f'w:bidi="{locale}"', tag)
        else:
            new = tag[:-2].rstrip() + f' w:bidi="{locale}"/>'
        return xml[: match.start()] + new + xml[match.end():]
    # No themeFontLang at all: add one. It must sit inside <w:settings>.
    if "</w:settings>" in xml:
        return xml.replace(
            "</w:settings>",
            f'<w:themeFontLang w:val="en-US" w:bidi="{locale}"/></w:settings>',
        )
    return xml
