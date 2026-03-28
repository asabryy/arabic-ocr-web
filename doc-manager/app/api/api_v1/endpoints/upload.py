import logging

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.services.storage import FileStorage

router = APIRouter()
logger = logging.getLogger("doc-manager.upload")


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    storage.save_file(user_id, file.filename, file.file)
    return {"filename": file.filename, "status": storage.get_status(user_id, file.filename)}
