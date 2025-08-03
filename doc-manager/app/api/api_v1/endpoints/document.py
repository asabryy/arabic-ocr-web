import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from fastapi.responses import FileResponse

from app.dependencies.storage import get_storage
from app.services.storage import FileStorage
from app.schemas.document import DocumentInfo

router = APIRouter()
logger = logging.getLogger("doc-manager.documents")

@router.get("/documents", response_model=List[DocumentInfo])
def list_user_documents(
    user_id: str = Query(...),
    storage: FileStorage = Depends(get_storage),
):
    logger.info(f"[GET /documents] Request received for user_id={user_id}")
    try:
        files = storage.list_files(user_id)
        logger.info(f"Found {len(files)} documents for user {user_id}")
        return files
    except Exception as e:
        logger.error(f"Error listing files for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list user documents")

@router.delete("/documents")
def delete_file(
    user_id: str = Query(...),
    filename: str = Query(...),
    storage: FileStorage = Depends(get_storage),
):
    logger.info(f"[DELETE /documents] Deleting '{filename}' for user_id={user_id}")
    try:
        storage.delete_file(user_id, filename)
        logger.info(f"Deleted file {filename}")
        return {"detail": "File deleted"}
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

@router.get("/download")
def download_file(
    user_id: str = Query(...),
    filename: str = Query(...),
    storage: FileStorage = Depends(get_storage),
):
    logger.info(f"⬇️ [GET /download] Request to download '{filename}' for user_id={user_id}")
    try:
        file_path = storage.get_path(user_id, filename)
        logger.info(f"Sending file {file_path}")
        return FileResponse(path=file_path, filename=filename)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        raise HTTPException(status_code=404, detail="File not found")
