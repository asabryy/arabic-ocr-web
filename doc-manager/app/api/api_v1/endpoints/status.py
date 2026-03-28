from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.services.storage import FileStorage

router = APIRouter()


@router.get("/documents/status")
def get_document_status(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    status = storage.get_status(user_id, filename)
    return {"filename": filename, "status": status}
