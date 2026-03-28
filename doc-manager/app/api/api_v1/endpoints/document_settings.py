import json
import os

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.core.config import settings
from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.services.storage import FileStorage

router = APIRouter()


@router.post("/documents/options")
def save_file_options(
    filename: str = Query(...),
    options: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    if not storage.file_exists(user_id, filename):
        raise HTTPException(status_code=404, detail="File does not exist")

    workspace = os.path.join(settings.UPLOAD_DIR, user_id)
    os.makedirs(workspace, exist_ok=True)
    settings_path = os.path.join(workspace, f"{filename}.settings.json")
    with open(settings_path, "w") as f:
        json.dump(options, f)

    return {"detail": "Options saved"}
