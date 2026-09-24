import io
import logging
import re
from urllib.parse import quote

import fitz  # PyMuPDF — used to cut a page range out of a stored PDF
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app import metrics
from app.db.session import get_engine
from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.models.conversion_attempt import (
    OUTCOME_ACCEPTED,
    OUTCOME_DAILY_PAGES_EXCEEDED,
    OUTCOME_ENQUEUE_FAILED,
)
from app.queue.task_queue import publish_task
from app.schemas.document import DocumentInfo
from app.services import quota
from app.services.local_storage import LocalFileStorage
from app.services.pdf import count_pages
from app.services.storage import FileStorage

router = APIRouter()
logger = logging.getLogger("doc-manager.documents")


# ── helpers shared with the trial router ─────────────────────────────────────

def read_bytes(storage: FileStorage, owner: str, filename: str) -> bytes:
    """Fetch a stored file's bytes (local path or R2 presigned URL)."""
    path_or_url = storage.get_path(owner, filename)
    if isinstance(storage, LocalFileStorage):
        with open(path_or_url, "rb") as f:
            return f.read()
    resp = httpx.get(path_or_url, timeout=120)
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="File not found")
    return resp.content


async def stream_download(
    storage: FileStorage, owner: str, filename: str, download_name: str
):
    """Stream a stored file to the client as an attachment.

    R2 objects are streamed *through* the backend: presigned URLs reject requests
    that also carry an Authorization header (which axios always sends), so the
    presigned URL is never handed to the browser.
    """
    path_or_url = storage.get_path(owner, filename)
    if isinstance(storage, LocalFileStorage):
        return FileResponse(path_or_url, filename=download_name)
    # HTTP headers must be latin-1: give an ASCII fallback plus the RFC 5987 UTF-8 form
    # so Arabic filenames survive (a raw non-ASCII value would fail to encode).
    ascii_name = download_name.encode("ascii", "ignore").decode().replace('"', "") or "document"
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(download_name)}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(path_or_url)
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="File not found")
            return StreamingResponse(
                content=response.aiter_bytes(),
                media_type="application/octet-stream",
                headers={"Content-Disposition": disposition},
            )
    except httpx.HTTPError as e:
        logger.exception("Download HTTP error for '%s': %s", filename, e)
        raise HTTPException(status_code=502, detail="Failed to fetch file from storage")


def _quota_402(code: str, message: str, limit: int, used: int, plan: str) -> HTTPException:
    metrics.QUOTA_REJECTIONS.labels(reason=code, plan=plan).inc()
    return HTTPException(
        status_code=402,
        detail={"code": code, "message": message, "limit": limit, "used": used, "plan": plan},
    )


# ── partial conversion ───────────────────────────────────────────────────────
#
# Half the documents people actually bring us are longer than the per-document cap
# (median 10 pages, mean 22, max 211), and the landing page advertises books. The
# old answer was a 402 with no way forward. Now a long document is converted a
# batch at a time: the API cuts `start..end` out of the stored PDF, stores that
# slice under its own name and queues *that*, so
#
#   * the worker needs no change at all — it already turns `<stem>.pdf` into
#     `<stem>.docx`, and the slice it receives contains exactly the pages paid for;
#   * the output names cannot collide (`book__p1-10.docx`, `book__p11-20.docx`);
#   * the quota reservation is the size of the slice, not of the book.
#
# Which ranges have been done is kept in the source document's metadata sidecar, so
# "continue from page 41" survives a reload, a new device and a redeploy.

PART_RE = re.compile(r"^(?P<stem>.+)__p(?P<start>\d+)-(?P<end>\d+)\.(?P<ext>[A-Za-z0-9]+)$")


def part_name(filename: str, start: int, end: int, ext: str = "pdf") -> str:
    stem = filename.rsplit(".", 1)[0]
    return f"{stem}__p{start}-{end}.{ext}"


def parse_part(filename: str) -> dict | None:
    """Split `book__p11-20.pdf` into its source document and page range, or None."""
    m = PART_RE.match(filename or "")
    if not m:
        return None
    return {
        "source": f"{m.group('stem')}.{m.group('ext')}",
        "start": int(m.group("start")),
        "end": int(m.group("end")),
    }


def _ranges(meta: dict) -> list[dict]:
    """Converted page ranges recorded on a source document, oldest page first."""
    out = []
    for r in meta.get("ranges") or []:
        try:
            start, end = int(r["start"]), int(r["end"])
        except (KeyError, TypeError, ValueError):
            continue  # a hand-edited or half-written sidecar must not break /convert
        out.append({
            "start": start,
            "end": end,
            "file": r.get("file") or "",
            "output": r.get("output") or "",
        })
    return sorted(out, key=lambda r: (r["start"], r["end"]))


def _covered(ranges: list[dict]) -> set[int]:
    pages: set[int] = set()
    for r in ranges:
        pages.update(range(r["start"], r["end"] + 1))
    return pages


def _next_batch(ranges: list[dict], total: int, cap: int) -> tuple[int, int] | None:
    """The next run of not-yet-converted pages, at most `cap` long.

    Stops at the first already-converted page so a user who converted 41-60 by hand
    does not get pages billed to them twice on the next click.
    """
    done = _covered(ranges)
    start = next((p for p in range(1, total + 1) if p not in done), None)
    if start is None:
        return None
    end = start
    while end + 1 <= total and (end + 1) not in done and (end + 1 - start + 1) <= cap:
        end += 1
    return start, end


def _progress(filename: str, meta: dict, cap: int) -> dict:
    """What has been converted of one document, and where to pick up."""
    total = meta.get("pages")
    ranges = _ranges(meta)
    converted = len(_covered(ranges))
    nxt = _next_batch(ranges, total, cap) if total else None
    return {
        "filename": filename,
        "total_pages": total,
        "converted_pages": converted,
        "remaining_pages": max(0, (total or 0) - converted),
        "ranges": ranges,
        "next_start_page": nxt[0] if nxt else None,
        "next_end_page": nxt[1] if nxt else None,
        "max_doc_pages": cap,
        # False for documents that were converted in one go the old way: those have
        # no recorded ranges and their own status carries the outcome.
        "partial": bool(ranges),
    }


def slice_pdf(pdf_bytes: bytes, start: int, end: int) -> bytes:
    """Bytes of a new PDF holding pages `start..end` (1-based, inclusive)."""
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        out = fitz.open()
        try:
            out.insert_pdf(src, from_page=start - 1, to_page=end - 1)
            return out.tobytes()
        finally:
            out.close()
    finally:
        src.close()


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get("/documents", response_model=list[DocumentInfo])
def list_user_documents(
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    try:
        return storage.list_files(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing files for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to list user documents")


@router.delete("/documents")
def delete_file(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    try:
        # A partially converted document owns the per-batch slices cut out of it.
        # Deleting the document has to take them with it, or the user pays storage
        # for pieces of a file they no longer have and sees orphan rows.
        for r in _ranges(storage.get_meta(user_id, filename)):
            if not r["file"]:
                continue
            try:
                storage.delete_file(user_id, r["file"])
            except HTTPException:
                pass  # already gone
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not delete batch '%s': %s", r["file"], e)

        storage.delete_file(user_id, filename)

        # Deleting one batch on its own reopens those pages for conversion.
        part = parse_part(filename)
        if part and storage.file_exists(user_id, part["source"]):
            meta = dict(storage.get_meta(user_id, part["source"]))
            kept = [r for r in _ranges(meta) if r["file"] != filename]
            if len(kept) != len(meta.get("ranges") or []):
                meta["ranges"] = kept
                storage.save_meta(user_id, part["source"], meta)

        return {"detail": "File deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting file '%s': %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to delete file")


@router.get("/usage")
def get_usage(
    user_id: str = Depends(get_current_user_id),
    engine: Engine = Depends(get_engine),
):
    """Today's page usage and the caller's plan limits (drives the UI meter)."""
    uid = int(user_id)
    try:
        plan = quota.get_plan(engine, uid)
        limits = quota.limits_for(plan)
        used = quota.used_today(engine, uid)
    except OperationalError as e:
        logger.error("Quota DB unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Quota service unavailable")
    return {
        "plan": limits.plan,
        "used_today": used,
        "daily_limit": limits.daily_pages,
        "max_doc_pages": limits.max_doc_pages,
        "resets_at": quota.next_reset().isoformat(),
    }


@router.post("/convert")
def convert_document(
    filename: str = Query(...),
    start_page: int | None = Query(
        None, ge=1, description="1-based first page to convert. Defaults to the first "
                                "page of this document that has not been converted yet."
    ),
    end_page: int | None = Query(
        None, ge=1, description="1-based last page (inclusive). Clamped to the end of "
                                "the document and to the plan's pages-per-batch limit."
    ),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
    engine: Engine = Depends(get_engine),
):
    """Queue a conversion of the whole document, or of one batch of its pages.

    A document within the plan's per-document limit behaves exactly as before: the
    whole file is queued and the output keeps its name. A longer one is no longer
    refused — the next unconverted batch is cut out and queued, and the response
    says which pages were taken and where to resume.
    """
    if not storage.file_exists(user_id, filename):
        raise HTTPException(status_code=404, detail="File not found")
    if storage.get_status(user_id, filename) == "processing":
        raise HTTPException(status_code=409, detail="Already processing")

    # Page count: persisted at upload; backfill for files uploaded before that existed.
    meta = dict(storage.get_meta(user_id, filename))
    pages = meta.get("pages")
    if pages is None:
        pages = count_pages(read_bytes(storage, user_id, filename))
        meta["pages"] = pages
        storage.save_meta(user_id, filename, meta)

    uid = int(user_id)
    try:
        plan = quota.get_plan(engine, uid)
        limits = quota.limits_for(plan)
        cap = limits.max_doc_pages
        done_ranges = _ranges(meta)

        # ── which pages are we converting? ──────────────────────────────────
        if start_page is None and end_page is None:
            if pages <= cap:
                first, last = 1, pages  # unchanged path: the whole document
            else:
                batch = _next_batch(done_ranges, pages, cap)
                if batch is None:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "already_converted",
                            "message": f"All {pages} pages of this document have "
                                       "already been converted.",
                        },
                    )
                first, last = batch
        else:
            first = start_page or 1
            if first > pages:
                raise HTTPException(
                    status_code=400,
                    detail=f"start_page {first} is past the end of this "
                           f"{pages}-page document.",
                )
            last = end_page if end_page is not None else first + cap - 1
            if last < first:
                raise HTTPException(
                    status_code=400, detail="end_page must not be before start_page."
                )
            # Clamp rather than refuse: an over-long request becomes a batch the
            # plan does allow, and the response reports what was actually taken.
            last = min(last, pages, first + cap - 1)

        batch_pages = last - first + 1
        partial = not (first == 1 and last == pages)
        slice_name = part_name(filename, first, last) if partial else filename
        output_name = part_name(filename, first, last, "docx") if partial else (
            filename.rsplit(".", 1)[0] + ".docx"
        )

        if partial and storage.get_status(user_id, slice_name) == "processing":
            raise HTTPException(status_code=409, detail="Already processing")
        if partial and storage.get_status(user_id, slice_name) == "done":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "already_converted",
                    "message": f"Pages {first}-{last} have already been converted.",
                },
            )

        # ── reserve exactly the pages this batch will consume ───────────────
        try:
            used_now = quota.reserve(engine, uid, batch_pages, limits.daily_pages, limits.plan)
        except quota.QuotaExceeded as e:
            quota.record_attempt(
                engine, uid, pages=batch_pages, outcome=OUTCOME_DAILY_PAGES_EXCEEDED,
                plan=e.plan, total_pages=pages, start_page=first, end_page=last,
            )
            logger.info(
                "convert refused user=%s file=%s pages=%d of %d reason=%s used=%d limit=%d",
                uid, filename, batch_pages, pages, e.code, e.used, e.limit,
            )
            raise _quota_402(
                e.code,
                f"You've used {e.used} of {e.limit} pages today on the {e.plan} plan.",
                e.limit, e.used, e.plan,
            )
    except OperationalError as e:
        logger.error("Quota DB unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Quota service unavailable")

    # ── cut the batch out of the stored PDF ─────────────────────────────────
    # Done after the reservation so a refusal never pays for the download+render,
    # and released again if it fails, exactly like a failed enqueue.
    if partial:
        try:
            storage.save_file(
                user_id, slice_name,
                io.BytesIO(slice_pdf(read_bytes(storage, user_id, filename), first, last)),
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to extract pages %d-%d of '%s': %s", first, last, filename, e)
            try:
                quota.release(engine, uid, batch_pages)
            except Exception as rel:  # noqa: BLE001
                logger.error("Failed to release %d pages for user %s: %s", batch_pages, uid, rel)
            quota.record_attempt(
                engine, uid, pages=batch_pages, outcome=OUTCOME_ENQUEUE_FAILED,
                plan=limits.plan, total_pages=pages, start_page=first, end_page=last,
            )
            raise HTTPException(status_code=500, detail="Failed to extract those pages")

    # Mark processing BEFORE publishing: a fast worker can finish and write "done"
    # before this line ran, and the old ordering then overwrote it with "processing".
    # For a batch it is the slice that gets the status — the source document is not
    # itself being converted, and would otherwise sit on "processing" forever.
    storage.set_status(user_id, slice_name, "processing")

    try:
        # The reservation day travels with the task. Refunding against "today at
        # refund time" lands on the wrong row for anything that crosses UTC
        # midnight, which zeroes a fresh day's counter and hands out free pages.
        task = {
            "file_id": slice_name,
            "user_id": user_id,
            "mode": "ocr",
            "pages": batch_pages,
            "reserved_day": quota.today().isoformat(),
        }
        if partial:
            # Additive and purely informational: `file_id` already points at a PDF
            # holding exactly these pages, so a worker running the previous image —
            # which reads this dict with .get() and ignores what it does not know —
            # produces the right output from the same message.
            task["source_file_id"] = filename
            task["source_page_start"] = first
            task["source_page_end"] = last
            task["source_total_pages"] = pages
        publish_task(task)
    except Exception as e:
        # Only the publish is guarded. Anything after it means the task IS queued,
        # and refunding then would give the pages back while the worker still runs.
        logger.error("Failed to queue task for '%s': %s", slice_name, e)
        metrics.ENQUEUE_FAILURES.labels(mode="ocr").inc()
        try:
            storage.set_status(user_id, slice_name, "pending")
        except Exception as rev:  # noqa: BLE001
            logger.error("Could not revert status for '%s': %s", slice_name, rev)
        if partial:
            try:
                storage.delete_file(user_id, slice_name)  # no orphan slice behind a failure
            except Exception as rm:  # noqa: BLE001
                logger.error("Could not remove slice '%s': %s", slice_name, rm)
        try:
            quota.release(engine, uid, batch_pages)
        except Exception as rel:  # noqa: BLE001
            logger.error("Failed to release %d pages for user %s: %s", batch_pages, uid, rel)
        quota.record_attempt(
            engine, uid, pages=batch_pages, outcome=OUTCOME_ENQUEUE_FAILED,
            plan=limits.plan, total_pages=pages, start_page=first, end_page=last,
        )
        raise HTTPException(status_code=503, detail="Failed to queue conversion task")

    # Record the range only once it is really queued, so the resume point never
    # points at a batch that was never sent.
    if partial:
        entry = {"start": first, "end": last, "file": slice_name, "output": output_name}
        meta["ranges"] = [r for r in _ranges(meta) if (r["start"], r["end"]) != (first, last)]
        meta["ranges"].append(entry)
        meta["ranges"].sort(key=lambda r: (r["start"], r["end"]))
        storage.save_meta(user_id, filename, meta)

    quota.record_attempt(
        engine, uid, pages=batch_pages, outcome=OUTCOME_ACCEPTED, plan=limits.plan,
        total_pages=pages, start_page=first, end_page=last,
    )
    metrics.CONVERSIONS_REQUESTED.labels(mode="ocr", plan=limits.plan).inc()
    metrics.PAGES_REQUESTED.labels(mode="ocr", plan=limits.plan).inc(batch_pages)
    logger.info(
        "convert accepted user=%s file=%s pages=%d-%d (%d of %d) plan=%s output=%s",
        uid, filename, first, last, batch_pages, pages, limits.plan, output_name,
    )

    progress = _progress(filename, meta, cap)
    return {
        "filename": filename,
        "status": "processing",
        "pages": batch_pages,
        "used_today": used_now,
        "daily_limit": limits.daily_pages,
        # ── partial conversion ──
        "partial": partial,
        "total_pages": pages,
        "start_page": first,
        "end_page": last,
        "output_filename": output_name,
        "part_filename": slice_name if partial else None,
        "converted_pages": progress["converted_pages"] if partial else pages,
        "remaining_pages": progress["remaining_pages"] if partial else 0,
        "next_start_page": progress["next_start_page"] if partial else None,
        "max_doc_pages": cap,
    }


@router.get("/conversion-progress")
def conversion_progress(
    filename: str | None = Query(
        None, description="One document; omit for every document the caller owns."
    ),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
    engine: Engine = Depends(get_engine),
):
    """Which pages of each document have been converted, and where to resume.

    This is what makes "continue from page 41" a thing the UI can offer: the ranges
    live in the document's metadata sidecar, not in the browser.
    """
    try:
        limits = quota.limits_for(quota.get_plan(engine, int(user_id)))
    except OperationalError as e:
        logger.error("Quota DB unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Quota service unavailable")

    if filename is not None:
        if not storage.file_exists(user_id, filename):
            raise HTTPException(status_code=404, detail="File not found")
        names = [filename]
    else:
        try:
            names = [
                f.filename for f in storage.list_files(user_id)
                if parse_part(f.filename) is None  # batches are parts, not documents
            ]
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            logger.error("Error listing files for user %s: %s", user_id, e)
            raise HTTPException(status_code=500, detail="Failed to list user documents")

    items = []
    for name in names:
        try:
            items.append(_progress(name, storage.get_meta(user_id, name), limits.max_doc_pages))
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not read progress for '%s': %s", name, e)
    return {"items": items, "max_doc_pages": limits.max_doc_pages, "plan": limits.plan}


@router.get("/preview")
async def preview_file(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    if isinstance(storage, LocalFileStorage):
        path = storage.get_path(user_id, filename)
        return FileResponse(
            path,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )

    signed_url = storage.get_path(user_id, filename)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(signed_url)
            if response.status_code != 200:
                logger.error("R2 preview fetch failed: %s", response.status_code)
                raise HTTPException(status_code=404, detail="PDF not found")
            return StreamingResponse(
                content=response.aiter_bytes(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={filename}"},
            )
    except httpx.HTTPError as e:
        logger.exception("Preview HTTP error for '%s': %s", filename, e)
        raise HTTPException(status_code=502, detail="Failed to fetch file from storage")


@router.get("/download")
async def download_file(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    try:
        response = await stream_download(storage, user_id, filename, filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Download failed for '%s': %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to download file")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    metrics.DOWNLOADS.labels(kind=ext if ext in ("docx", "pdf") else "other").inc()
    return response
