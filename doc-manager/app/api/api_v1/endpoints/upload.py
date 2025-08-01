from fastapi import APIRouter, Depends, UploadFile, File, Form
from app.dependencies.storage import get_storage
from app.services.storage import FileStorage

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    storage: FileStorage = Depends(get_storage),
):
    path = storage.save_file(user_id, file.filename, file.file)
    return {"message": "Uploaded", "path": path}