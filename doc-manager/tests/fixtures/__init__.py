"""Generated test documents, and the known-correct answers for them.

The expectations live here beside the generator so the two cannot drift: if the
fixture's content changes, the strings asserted against it change in the same
file.
"""

from pathlib import Path

from .make_fixture import build

FIXTURE_PDF = Path(__file__).parent / "fixture_arabic.pdf"

# Exactly as the fixture's source HTML writes them. Every one of these is a
# documented failure mode of naive Arabic extraction.
EXPECT_MIXED_LINE = "المبلغ المعتمد هو 1500 SAR"       # digits and Latin, in order
EXPECT_REFERENCE = "HR-2026/14"                         # a token with inner punctuation
EXPECT_BODY = "تصرف المنشأة بدل السكن للموظفين"
EXPECT_HEADING = "سياسة الموارد البشرية"
# White text on a filled band: invisible unless the fill is carried too.
EXPECT_BAND_TITLE = "إدارة الموارد البشرية"
EXPECT_BAND_FILL = "996600"
EXPECT_SUBHEADING = "أولاً: بدل السكن"

# The table, in the source's own column order: column 0 is the RIGHTMOST cell.
EXPECT_TABLE_HEADER = ["الدرجة", "البدل الشهري", "العملة"]
EXPECT_TABLE_ROWS = [
    ["الأولى", "2500", "SAR"],
    ["الثانية", "1800", "SAR"],
    ["الثالثة", "1200", "SAR"],
]

# What must NOT appear: each is what a specific bug produces.
REJECT = {
    "0051": "digits reversed by the RTL sort",
    "RAS": "Latin reversed by the RTL sort",
    "SAR 1500": "LTR island reversed as one unit instead of per token",
    "ةجردلا": "table cell text taken from the finder in visual order",
}


def arabic_page(html: str, *, width: float = 595, height: float = 842,
                draw=None) -> bytes:
    """A one-page PDF whose Arabic is really shaped, for ad-hoc test documents.

    Always use this rather than ``page.insert_text`` for Arabic: insert_text paints
    glyphs in the order given with no shaping or bidi, and for a font without the
    glyphs it emits placeholder dots — so a test written on it asserts against
    "····· ······" and proves nothing.

    ``draw`` receives the page before the text, for ruling lines or fills.
    """
    import pymupdf

    from .make_fixture import CSS

    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    if draw is not None:
        draw(page, pymupdf)
    page.insert_htmlbox(pymupdf.Rect(20, 20, width - 20, height - 20), html, css=CSS)
    data = doc.tobytes()
    doc.close()
    return data


def ensure_fixture() -> Path:
    """Build the fixture if it is not already on disk, and return its path."""
    if not FIXTURE_PDF.exists():
        build(FIXTURE_PDF)
    return FIXTURE_PDF
