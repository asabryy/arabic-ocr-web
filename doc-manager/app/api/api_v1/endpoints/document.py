from fastapi import APIRouter, Depends, Query
from typing import List
from app.dependencies.storage import get_storage
from app.services.storage import FileStorage
from app.schemas.document import DocumentInfo
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/documents", response_model=List[DocumentInfo])
def list_user_documents(
    user_id: str = Query(...),
    storage: FileStorage = Depends(get_storage),
):
    return storage.list_files(user_id)

@router.delete("/documents")
def delete_file(user_id: str = Query(...), filename: str = Query(...), storage: FileStorage = Depends(get_storage)):
    storage.delete_file(user_id, filename)
    return {"detail": "File deleted"}

@router.get("/download")
def download_file(user_id: str = Query(...), filename: str = Query(...), storage: FileStorage = Depends(get_storage)):
    file_path = storage.get_path(user_id, filename)  # Add this method to LocalFileStorage
    return FileResponse(path=file_path, filename=filename)
