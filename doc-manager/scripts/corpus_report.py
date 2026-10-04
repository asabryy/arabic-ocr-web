"""Measure the route split over the real document corpus.

Answers what no synthetic fixture can: what fraction of actual user uploads are
born-digital, which producers they come from, and how often each triage signal
fires. Run it before and after a change to the triage rules — a shift in the split
is the first sign a threshold moved too far.

READS ONLY, and never writes document content anywhere: the report carries counts,
ratios and the PDF producer string, nothing else. Files are downloaded to a scratch
directory one at a time and deleted immediately.

Needs R2 credentials in doc-manager/.env (R2_ENDPOINT_URL, R2_ACCESS_KEY_ID,
R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME).

    cd doc-manager && SECRET_KEY=dummy PYTHONPATH=$PWD .venv/bin/python \
        scripts/corpus_report.py [--limit 100]

Baseline as of 2026-10-03, 293 documents / 11,336 pages:
    digital 71% of docs, 72% of pages; of digital, 76% clean,
    23% batched tashkeel, 1.4% broken ToUnicode.
"""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCRATCH = Path(tempfile.gettempdir()) / "textara-corpus"


from app.core.config import settings  # noqa: E402


def s3_client():
    import boto3
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    ), os.environ["R2_BUCKET_NAME"]


def list_pdfs(s3, bucket, limit=None):
    out = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for o in page.get("Contents", []):
            if o["Key"].lower().endswith(".pdf"):
                out.append((o["Key"], o["Size"]))
                if limit and len(out) >= limit:
                    return out
    return out


def inspect(doc) -> dict:
    """Digital, scanned, or mixed — and what produced it."""
    n = len(doc)
    text_pages = scan_pages = 0
    for i in range(n):
        page = doc[i]
        chars = len("".join(page.get_text("text").split()))
        area = abs(page.rect.get_area()) or 1.0
        img_area = 0.0
        for img in page.get_images(full=True):
            for r in page.get_image_rects(img[0]):
                img_area += abs(r.get_area())
        coverage = min(img_area / area, 1.0)
        if chars >= 50:
            text_pages += 1
        elif coverage > 0.5:
            scan_pages += 1

    meta = doc.metadata or {}
    producer = (meta.get("producer") or meta.get("creator") or "unknown").strip()[:60]

    if text_pages == 0:
        kind = "scanned"
    elif scan_pages == 0:
        kind = "digital"
    elif text_pages >= n * 0.8:
        kind = "digital"
    else:
        kind = "mixed"
    return {"kind": kind, "pages": n, "text_pages": text_pages,
            "scan_pages": scan_pages, "producer": producer}


def analyse(path: Path) -> dict:
    """Triage + extraction quality signals for one PDF."""
    import pymupdf

    from app.ocr import digital as D
    from app.ocr import triage as T

    t0 = time.perf_counter()
    doc = pymupdf.open(path)
    tri = inspect(doc)
    rec = dict(tri)

    if tri["kind"] == "scanned":
        doc.close()
        rec.update(elapsed_s=round(time.perf_counter() - t0, 2),
                   headings=0, runs=0, suspect=0, batching=0.0, error=None)
        return rec

    idx = list(range(min(len(doc), 25)))     # cap work per document
    try:
        prof = D.document_profile(doc, idx)
        col = D.document_column(doc, idx)
        headings = runs = suspect = 0
        marks_total = marks_dup = 0
        for i in idx:
            blocks, _ = D.extract_page(doc[i], D.STYLE_SOURCE, prof, col)
            headings += sum(1 for b in blocks if b.kind == "heading")
            for b in blocks:
                runs += len(b.runs)
            suspect += T._suspect_chars(doc[i])
            m, d = T._mark_counts(doc[i])
            marks_total += m
            marks_dup += d
        # Pooled over the document, and only meaningful above a floor of marks.
        ratio = (marks_dup / marks_total
                 if marks_total >= settings.DIGITAL_MIN_MARKS_FOR_BATCHING else 0.0)
        rec.update(headings=headings, runs=runs, suspect=suspect,
                   marks=marks_total, batching=round(ratio, 3), error=None)
    except Exception as e:  # noqa: BLE001 — a bad file must not stop the sweep
        rec.update(headings=0, runs=0, suspect=0, batching=0.0,
                   error=f"{type(e).__name__}: {e}"[:120])
    finally:
        doc.close()

    rec["elapsed_s"] = round(time.perf_counter() - t0, 2)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=str(ROOT / "corpus_results.json"))
    args = ap.parse_args()

    SCRATCH.mkdir(parents=True, exist_ok=True)
    s3, bucket = s3_client()
    keys = list_pdfs(s3, bucket, args.limit)
    print(f"{len(keys)} PDF(s) in {bucket}\n")

    results = []
    for n, (key, size) in enumerate(keys, 1):
        local = SCRATCH / f"{n:04d}.pdf"
        try:
            s3.download_file(bucket, key, str(local))
        except Exception as e:  # noqa: BLE001
            print(f"  [{n}/{len(keys)}] download failed: {type(e).__name__}")
            results.append({"key_hash": hash(key) & 0xFFFFFF, "error": "download"})
            continue
        try:
            rec = analyse(local)
        except Exception:  # noqa: BLE001
            rec = {"kind": "error", "error": traceback.format_exc(limit=1)[:120]}
        # The key can contain a user id and filename; only a digest is kept.
        rec["id"] = f"{n:04d}"
        rec["bytes"] = size
        results.append(rec)
        local.unlink(missing_ok=True)

        flag = ""
        if rec.get("error"):
            flag = "  ERROR"
        elif rec.get("batching", 0) > 0.10:
            flag = "  tashkeel-batched"
        elif rec.get("suspect", 0) > 0:
            flag = f"  suspect={rec['suspect']}"
        print(f"  [{n}/{len(keys)}] {rec.get('kind','?'):8s} "
              f"{rec.get('pages',0):4d}p  {rec.get('elapsed_s',0):6.2f}s{flag}")

    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    report(results)
    print(f"\nraw: {args.out}")


def report(results):
    ok = [r for r in results if not r.get("error") and r.get("kind") != "error"]
    print("\n" + "=" * 62)
    print(f"{len(results)} document(s), {len(ok)} analysed")

    kinds = Counter(r["kind"] for r in ok)
    total_pages = sum(r.get("pages", 0) for r in ok)
    print("\nDOCUMENT TYPE")
    for k, c in kinds.most_common():
        pages = sum(r.get("pages", 0) for r in ok if r["kind"] == k)
        print(f"  {k:10s} {c:4d} docs ({c/max(len(ok),1):5.1%})   {pages:6d} pages "
              f"({pages/max(total_pages,1):5.1%})")

    print("\nPRODUCER")
    for p, c in Counter(r.get("producer", "unknown") for r in ok).most_common(12):
        print(f"  {c:4d}  {p or '(empty)'}")

    digital = [r for r in ok if r["kind"] in ("digital", "mixed")]
    if digital:
        print(f"\nQUALITY SIGNALS (over {len(digital)} digital/mixed docs)")
        batched = [r for r in digital if r.get("batching", 0) > 0.10]
        suspect = [r for r in digital if r.get("suspect", 0) > 0]
        clean = [r for r in digital
                 if r.get("batching", 0) <= 0.10 and r.get("suspect", 0) == 0]
        print(f"  clean                  {len(clean):4d} ({len(clean)/len(digital):5.1%})")
        print(f"  tashkeel batched       {len(batched):4d} ({len(batched)/len(digital):5.1%})")
        print(f"  broken ToUnicode       {len(suspect):4d} ({len(suspect)/len(digital):5.1%})")
        times = [r["elapsed_s"] for r in digital if r.get("elapsed_s")]
        pages = [r["pages"] for r in digital if r.get("pages")]
        if times:
            print(f"\n  time/doc  median {statistics.median(times):.2f}s   "
                  f"max {max(times):.2f}s")
        if pages:
            print(f"  pages/doc median {statistics.median(pages):.0f}   "
                  f"max {max(pages)}")

    errs = [r for r in results if r.get("error")]
    if errs:
        print(f"\nERRORS ({len(errs)})")
        for e, c in Counter(r["error"].split(":")[0] for r in errs).most_common(6):
            print(f"  {c:4d}  {e}")


if __name__ == "__main__":
    main()
