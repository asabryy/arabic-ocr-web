"""
Build the Arabic test PDF the digital-extraction tests assert against.

Real sample documents have no tables, no running heads and no mixed
Arabic/Latin/digit lines, so those branches would go untested. This writes a
born-digital Arabic PDF containing all of them whose correct extraction is known
in advance, which is what turns the tests into assertions rather than snapshots.

It uses insert_htmlbox, not insert_text: insert_text paints glyphs in the order
given with no shaping or bidi, producing a PDF full of disconnected, backwards
Arabic — a fixture that would test nothing. insert_htmlbox runs a real layout
engine and emits shaped presentation forms in logical order, which is what Word
and InDesign produce.

The fixture is generated rather than committed as a binary so it can be rebuilt
when the expectations change, and so the expectations live next to the content
that produces them.
"""

import argparse
from pathlib import Path

import pymupdf

REG = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"

CSS = f"""
@font-face {{ font-family: nn; src: url({REG}); }}
@font-face {{ font-family: nn; font-weight: bold; src: url({BOLD}); }}
* {{ font-family: nn; direction: rtl; }}
body {{ font-size: 12px; color: #000; }}
h1 {{ font-size: 20px; color: #bf0000; text-decoration: underline; text-align: center; }}
h2 {{ font-size: 14px; color: #bf0000; text-decoration: underline; }}
p  {{ font-size: 12px; text-align: justify; }}
.head {{ font-size: 9px; color: #000; text-align: center; }}
.num  {{ font-size: 10px; text-align: center; }}
table {{ border-collapse: collapse; width: 100%; direction: rtl; }}
td, th {{ border: 1px solid #000; padding: 4px 8px; font-size: 11px; }}
th {{ font-weight: bold; }}
"""

RUNNING_HEAD = "دليل سياسات الموارد البشرية"

PAGE1 = """
<h1>سياسة الموارد البشرية</h1>
<h2>أولاً: بدل السكن</h2>
<p>تصرف المنشأة بدل السكن للموظفين وفق الجدول المرفق أدناه، ويستحق الموظف
البدل بعد إتمام سنة كاملة في الخدمة لدى المنشأة.</p>
<p>المبلغ المعتمد هو 1500 SAR ويُراجع سنوياً حسب المرجع HR-2026/14.</p>
<table>
  <tr><th>الدرجة</th><th>البدل الشهري</th><th>العملة</th></tr>
  <tr><td>الأولى</td><td>2500</td><td>SAR</td></tr>
  <tr><td>الثانية</td><td>1800</td><td>SAR</td></tr>
  <tr><td>الثالثة</td><td>1200</td><td>SAR</td></tr>
</table>
"""

PAGE2 = """
<h2>ثانياً: بدل النقل</h2>
<p>يصرف بدل النقل شهرياً لجميع الموظفين المستحقين وفق اللوائح الداخلية
المعتمدة من الإدارة العليا.</p>
<ul>
  <li>الموظفون الدائمون: بدل كامل.</li>
  <li>الموظفون المتعاقدون: نصف البدل.</li>
</ul>
"""


def build(out_path: Path) -> None:
    doc = pymupdf.open()
    for page_no, html in ((1, PAGE1), (2, PAGE2)):
        page = doc.new_page(width=595, height=842)

        # Single-rule page border — deliberately unlike the corpus's double frame,
        # so border detection is tested on a second shape.
        page.draw_rect(pymupdf.Rect(30, 30, 565, 812), color=(0, 0, 0), width=1.5)

        # Running head, same on both pages: it must reach the DOCX header rather
        # than the body.
        page.insert_htmlbox(pymupdf.Rect(60, 45, 535, 70),
                            f'<div class="head">{RUNNING_HEAD}</div>', css=CSS)

        page.insert_htmlbox(pymupdf.Rect(60, 90, 535, 700), html, css=CSS)

        page.insert_htmlbox(pymupdf.Rect(250, 780, 345, 802),
                            f'<div class="num">{page_no}</div>', css=CSS)

    doc.save(out_path)
    doc.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "fixture_arabic.pdf"))
    args = ap.parse_args()
    out = Path(args.out)
    build(out)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    print("  expected: running head on both pages, 1 table (4x3, rightmost column")
    print("            = الدرجة), 2 red underlined headings, a bullet list,")
    print("            mixed Arabic/Latin/digit lines, page numbers 1-2,")
    print("            single-rule border")


if __name__ == "__main__":
    main()
