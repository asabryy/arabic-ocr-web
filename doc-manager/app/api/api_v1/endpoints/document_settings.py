from fastapi import APIRouter, Depends, Body, Query, HTTPException
from typing import Optional
import os, json

from app.core.config import settings

router = APIRouter()

@router.post("/documents/options")
def save_file_options(
    user_id: str = Query(...),
    filename: str = Query(...),
    options: dict = Body(...)
):
    workspace = os.path.join(settings.UPLOAD_DIR, user_id)
    file_path = os.path.join(workspace, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File does not exist")

    settings_path = os.path.join(workspace, f"{filename}.settings.json")
    with open(settings_path, "w") as f:
        json.dump(options, f)

    return {"detail": "Options saved"} #test rednder.com deployment