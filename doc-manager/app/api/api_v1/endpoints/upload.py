import io
import logging

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.services.pdf import count_pages
from app.services.storage import FileStorage

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
    data = await file.read()
    pages = count_pages(data)
    storage.save_file(user_id, file.filename, io.BytesIO(data))
    storage.save_meta(user_id, file.filename, {"pages": pages})
    return {
        "filename": file.filename,
        "status": storage.get_status(user_id, file.filename),
        "pages": pages,
    }
