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


def ensure_fixture() -> Path:
    """Build the fixture if it is not already on disk, and return its path."""
    if not FIXTURE_PDF.exists():
        build(FIXTURE_PDF)
    return FIXTURE_PDF
