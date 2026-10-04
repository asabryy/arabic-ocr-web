"""Produce a review set: real documents converted both ways, beside their sources.

Nothing automated can tell whether the Arabic is RIGHT. The corpus report says
extraction produced something plausible; a document can pass every machine check
while quietly mangling a name. So this picks real documents spanning the corpus's
producer mix, converts each in both styles, and writes them next to their source
PDF for a human to read.

    cd doc-manager && SECRET_KEY=dummy PYTHONPATH=$PWD .venv/bin/python \\
        scripts/make_review_samples.py [--out /tmp/review] [--per-producer 1]
"""

import argparse
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def s3_client():
    import boto3
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    missing = [k for k in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID",
                           "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
               if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing credentials in {ROOT / '.env'}: {', '.join(missing)}")
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    ), os.environ["R2_BUCKET_NAME"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/textara-review")
    ap.add_argument("--per-producer", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=12,
                    help="cap pages per sample so the reviewer is reading, not scrolling")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    import fitz

    from app.ocr import triage
    from app.ocr.digital import process_pdf_digital
    from app.ocr.styled_builder import STYLE_SOURCE, STYLE_UNIFORM

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    s3, bucket = s3_client()

    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        keys += [o["Key"] for o in page.get("Contents", [])
                 if o["Key"].lower().endswith(".pdf")]
    random.Random(args.seed).shuffle(keys)
    print(f"{len(keys)} PDFs in {bucket}; looking for documents the digital path takes\n")

    tmp = out / "_src.pdf"
    chosen: dict[str, int] = defaultdict(int)
    made = 0

    for key in keys:
        if made >= args.per_producer * 8:
            break
        try:
            s3.download_file(bucket, key, str(tmp))
            data = tmp.read_bytes()
        except Exception:  # noqa: BLE001
            continue

        decision = triage.classify(data)
        # Only documents that would actually take the digital path are worth
        # reviewing: the rest go to Gemini and are unchanged by this work.
        if not decision.is_digital:
            continue
        producer = (decision.producer or "unknown").split("(")[0].strip()[:28]
        if chosen[producer] >= args.per_producer:
            continue

        slug = "".join(c if c.isalnum() else "-" for c in producer).strip("-").lower()
        stem = f"{made + 1:02d}-{slug or 'unknown'}"
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            clipped = fitz.open()
            clipped.insert_pdf(doc, from_page=0,
                               to_page=min(args.max_pages, len(doc)) - 1)
            source = clipped.tobytes()
            doc.close()
            clipped.close()

            (out / f"{stem}__SOURCE.pdf").write_bytes(source)
            (out / f"{stem}__match-original.docx").write_bytes(
                process_pdf_digital(source, style=STYLE_SOURCE))
            (out / f"{stem}__clean.docx").write_bytes(
                process_pdf_digital(source, style=STYLE_UNIFORM))
        except Exception as e:  # noqa: BLE001
            print(f"  skipped {stem}: {type(e).__name__}: {e}")
            continue

        chosen[producer] += 1
        made += 1
        print(f"  {stem:34s} {decision.pages:4d}p  {producer}")

    tmp.unlink(missing_ok=True)
    print(f"\n{made} sample(s) in {out}")
    print("Each has a __SOURCE.pdf and two conversions. Read the Arabic in the "
          "DOCX against the PDF:\n"
          "  - are words and letters in the right order?\n"
          "  - are names and numbers intact?\n"
          "  - do headings, lists and tables land where they should?")


if __name__ == "__main__":
    main()
