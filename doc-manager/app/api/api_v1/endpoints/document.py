import logging
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app import metrics
from app.db.session import get_engine
from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
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
        storage.delete_file(user_id, filename)
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
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
    engine: Engine = Depends(get_engine),
):
    if not storage.file_exists(user_id, filename):
        raise HTTPException(status_code=404, detail="File not found")
    if storage.get_status(user_id, filename) == "processing":
        raise HTTPException(status_code=409, detail="Already processing")

    # Page count: persisted at upload; backfill for files uploaded before that existed.
    pages = storage.get_meta(user_id, filename).get("pages")
    if pages is None:
        pages = count_pages(read_bytes(storage, user_id, filename))
        storage.save_meta(user_id, filename, {"pages": pages})

    uid = int(user_id)
    try:
        plan = quota.get_plan(engine, uid)
        limits = quota.limits_for(plan)
        if pages > limits.max_doc_pages:
            raise _quota_402(
                "doc_pages_exceeded",
                f"This document has {pages} pages; the {limits.plan} plan allows up to "
                f"{limits.max_doc_pages} pages per document.",
                limits.max_doc_pages, pages, limits.plan,
            )
        try:
            used_now = quota.reserve(engine, uid, pages, limits.daily_pages, limits.plan)
        except quota.QuotaExceeded as e:
            raise _quota_402(
                e.code,
                f"You've used {e.used} of {e.limit} pages today on the {e.plan} plan.",
                e.limit, e.used, e.plan,
            )
    except OperationalError as e:
        logger.error("Quota DB unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Quota service unavailable")

    # Mark processing BEFORE publishing: a fast worker can finish and write "done"
    # before this line ran, and the old ordering then overwrote it with "processing".
    storage.set_status(user_id, filename, "processing")

    try:
        # The reservation day travels with the task. Refunding against "today at
        # refund time" lands on the wrong row for anything that crosses UTC
        # midnight, which zeroes a fresh day's counter and hands out free pages.
        publish_task({
            "file_id": filename,
            "user_id": user_id,
            "mode": "ocr",
            "pages": pages,
            "reserved_day": quota.today().isoformat(),
        })
    except Exception as e:
        # Only the publish is guarded. Anything after it means the task IS queued,
        # and refunding then would give the pages back while the worker still runs.
        logger.error("Failed to queue task for '%s': %s", filename, e)
        metrics.ENQUEUE_FAILURES.labels(mode="ocr").inc()
        try:
            storage.set_status(user_id, filename, "pending")
        except Exception as rev:  # noqa: BLE001
            logger.error("Could not revert status for '%s': %s", filename, rev)
        try:
            quota.release(engine, uid, pages)
        except Exception as rel:  # noqa: BLE001
            logger.error("Failed to release %d pages for user %s: %s", pages, uid, rel)
        raise HTTPException(status_code=503, detail="Failed to queue conversion task")

    metrics.CONVERSIONS_REQUESTED.labels(mode="ocr", plan=limits.plan).inc()
    metrics.PAGES_REQUESTED.labels(mode="ocr", plan=limits.plan).inc(pages)

    return {
        "filename": filename,
        "status": "processing",
        "pages": pages,
        "used_today": used_now,
        "daily_limit": limits.daily_pages,
    }


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
        return await stream_download(storage, user_id, filename, filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Download failed for '%s': %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to download file")
