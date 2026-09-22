import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app import metrics
from app.core.config import settings
from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.services.pdf import count_pages
from app.services.storage import FileStorage, safe_name

router = APIRouter()
logger = logging.getLogger("doc-manager.upload")


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    # Count pages once, while the bytes are in memory, and persist alongside the file.
    # Upload itself is not quota-gated: the user keeps the file; limits apply at /convert.
    # The multipart filename is attacker-controlled; pin it once here so the same
    # validated name is what gets stored, recorded and echoed back.
    filename = safe_name(file.filename or "")

    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is larger than the {settings.MAX_UPLOAD_MB} MB limit.",
        )

    pages = count_pages(data)
    storage.save_file(user_id, filename, io.BytesIO(data))
    storage.save_meta(user_id, filename, {"pages": pages})
    metrics.UPLOADS.inc()
    return {
        "filename": filename,
        "status": storage.get_status(user_id, filename),
        "pages": pages,
    }
