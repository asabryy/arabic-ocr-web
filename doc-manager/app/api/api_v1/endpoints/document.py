import logging
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse
import httpx

from app.dependencies.storage import get_storage
from app.services.storage import FileStorage
from app.schemas.document import DocumentInfo
from app.services.local_storage import LocalFileStorage
from app.services.r2_storage import R2FileStorage

router = APIRouter()
logger = logging.getLogger("doc-manager.documents")


@router.get("/documents", response_model=List[DocumentInfo])
def list_user_documents(
    user_id: str = Query(...),
    storage: FileStorage = Depends(get_storage),
):
    logger.info(f"[GET /documents] Listing documents for user_id={user_id}")
    try:
        return storage.list_files(user_id)
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
        return {"detail": "File deleted"}
    except Exception as e:
        logger.error(f"Error deleting file '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@router.get("/preview")
async def preview_file(
    user_id: str = Query(...),
    filename: str = Query(...),
    storage: FileStorage = Depends(get_storage),
):
    logger.info(f"🖼️ [GET /preview] Streaming preview for '{filename}' (user_id={user_id})")
    try:
        signed_url = storage.get_path(user_id, filename)

        async with httpx.AsyncClient() as client:
            response = await client.get(signed_url)

            if response.status_code != 200:
                logger.error(f"Preview fetch failed: {response.status_code} {response.text}")
                raise HTTPException(status_code=404, detail="PDF not found")

            content_type = response.headers.get("Content-Type", "")
            if "application/pdf" not in content_type:
                logger.error(f"Preview failed: invalid content type '{content_type}'")
                raise HTTPException(status_code=400, detail="Invalid PDF file")

            return StreamingResponse(
                content=response.aiter_bytes(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={filename}"},
            )
    except Exception as e:
        logger.exception(f"Preview failed for '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Failed to preview file")


@router.get("/download")
def download_file(
    user_id: str = Query(...),
    filename: str = Query(...),
    storage: FileStorage = Depends(get_storage),
):
    logger.info(f"⬇[GET /download] Download requested for '{filename}' (user_id={user_id})")

    try:
        path_or_url = storage.get_path(user_id, filename)

        if isinstance(storage, R2FileStorage):
            logger.info(f"Redirecting to R2 signed URL: {path_or_url}")
            return RedirectResponse(path_or_url)

        elif isinstance(storage, LocalFileStorage):
            logger.info(f"Serving local file: {path_or_url}")
            return FileResponse(
                path_or_url,
                media_type="application/pdf",
                filename=filename,
            )

        else:
            logger.error("Unknown storage backend used.")
            raise HTTPException(status_code=500, detail="Invalid storage configuration")

    except Exception as e:
        logger.exception(f"Download failed for '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")
