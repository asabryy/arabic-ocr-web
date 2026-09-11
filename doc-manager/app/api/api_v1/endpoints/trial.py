"""Anonymous landing-page trial: OCR the first page(s) of a PDF, no account required.

Files live under a synthetic owner prefix ``trial/<uuid4 hex>`` so the existing
FileStorage backends and the worker are reused unchanged (the worker just receives a
``max_pages`` cap). The unguessable trial id is the only credential for status and
download — deliberately no IP binding, since mobile clients change address.
"""

import io
import logging
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.api_v1.endpoints.document import stream_download
from app.core.config import settings
from app.core.rate_limit import limiter
from app.dependencies.storage import get_storage
from app.queue.task_queue import publish_task
from app.services.pdf import count_pages
from app.services.storage import FileStorage

router = APIRouter()
logger = logging.getLogger("doc-manager.trial")

TRIAL_ID_RE = re.compile(r"^[0-9a-f]{32}$")
TRIAL_PDF = "document.pdf"
TRIAL_DOCX = "document.docx"


def _owner(trial_id: str) -> str:
    # Strict id format keeps the storage prefix free of path/key games.
    if not TRIAL_ID_RE.match(trial_id or ""):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    return f"trial/{trial_id}"


@router.post("", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.TRIAL_RATE_LIMIT)
async def start_trial(
    request: Request,
    file: UploadFile = File(...),
    storage: FileStorage = Depends(get_storage),
):
    data = await file.read()
    if len(data) > settings.TRIAL_MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Trial uploads are limited to {settings.TRIAL_MAX_UPLOAD_MB} MB",
        )
    pages_total = count_pages(data)

    trial_id = uuid.uuid4().hex
    owner = _owner(trial_id)
    storage.save_file(owner, TRIAL_PDF, io.BytesIO(data))
    storage.save_meta(
        owner,
        TRIAL_PDF,
        {
            "pages": pages_total,
            "original_name": file.filename or TRIAL_PDF,
            "max_pages": settings.TRIAL_MAX_PAGES,
        },
    )
    try:
        publish_task(
            {
                "file_id": TRIAL_PDF,
                "user_id": owner,
                "mode": "trial",
                "max_pages": settings.TRIAL_MAX_PAGES,
            }
        )
        storage.set_status(owner, TRIAL_PDF, "processing")
    except Exception as e:
        logger.error("Failed to queue trial %s: %s", trial_id, e)
        try:
            storage.delete_file(owner, TRIAL_PDF)
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(status_code=503, detail="Failed to queue conversion task")

    logger.info("trial started id=%s pages_total=%d", trial_id, pages_total)
    return {
        "trial_id": trial_id,
        "pages_total": pages_total,
        "max_pages": settings.TRIAL_MAX_PAGES,
        "status": "processing",
    }


@router.get("/{trial_id}/status")
def trial_status(trial_id: str, storage: FileStorage = Depends(get_storage)):
    owner = _owner(trial_id)
    if not storage.file_exists(owner, TRIAL_PDF):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    meta = storage.get_meta(owner, TRIAL_PDF)
    return {
        "trial_id": trial_id,
        "status": storage.get_status(owner, TRIAL_PDF),
        "pages_total": meta.get("pages"),
        "max_pages": meta.get("max_pages", settings.TRIAL_MAX_PAGES),
    }


@router.get("/{trial_id}/download")
async def trial_download(trial_id: str, storage: FileStorage = Depends(get_storage)):
    owner = _owner(trial_id)
    if not storage.file_exists(owner, TRIAL_PDF):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    if storage.get_status(owner, TRIAL_PDF) != "done":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversion not finished")
    original = storage.get_meta(owner, TRIAL_PDF).get("original_name") or TRIAL_PDF
    download_name = original.rsplit(".", 1)[0] + ".docx"
    return await stream_download(storage, owner, TRIAL_DOCX, download_name)
