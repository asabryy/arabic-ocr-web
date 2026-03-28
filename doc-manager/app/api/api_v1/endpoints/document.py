import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.dependencies.auth import get_current_user_id
from app.dependencies.storage import get_storage
from app.queue.task_queue import publish_task
from app.schemas.document import DocumentInfo
from app.services.local_storage import LocalFileStorage
from app.services.storage import FileStorage

router = APIRouter()
logger = logging.getLogger("doc-manager.documents")


@router.get("/documents", response_model=list[DocumentInfo])
def list_user_documents(
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    try:
        return storage.list_files(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing files for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to list user documents")


@router.delete("/documents")
def delete_file(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    try:
        storage.delete_file(user_id, filename)
        return {"detail": "File deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting file '%s': %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to delete file")


@router.post("/convert")
def convert_document(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    if not storage.file_exists(user_id, filename):
        raise HTTPException(status_code=404, detail="File not found")
    if storage.get_status(user_id, filename) == "processing":
        raise HTTPException(status_code=409, detail="Already processing")
    try:
        publish_task({"file_id": filename, "user_id": user_id, "mode": "ocr"})
        storage.set_status(user_id, filename, "processing")
    except Exception as e:
        logger.error("Failed to queue task for '%s': %s", filename, e)
        raise HTTPException(status_code=503, detail="Failed to queue conversion task")
    return {"filename": filename, "status": "processing"}


@router.get("/preview")
async def preview_file(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    if isinstance(storage, LocalFileStorage):
        path = storage.get_path(user_id, filename)
        return FileResponse(
            path,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )

    signed_url = storage.get_path(user_id, filename)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(signed_url)
            if response.status_code != 200:
                logger.error("R2 preview fetch failed: %s", response.status_code)
                raise HTTPException(status_code=404, detail="PDF not found")
            return StreamingResponse(
                content=response.aiter_bytes(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={filename}"},
            )
    except httpx.HTTPError as e:
        logger.exception("Preview HTTP error for '%s': %s", filename, e)
        raise HTTPException(status_code=502, detail="Failed to fetch file from storage")


@router.get("/download")
async def download_file(
    filename: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    storage: FileStorage = Depends(get_storage),
):
    try:
        path_or_url = storage.get_path(user_id, filename)

        if isinstance(storage, LocalFileStorage):
            return FileResponse(path_or_url, filename=filename)

        # R2: stream through the backend — presigned URLs reject requests that
        # also carry an Authorization header (which axios always sends).
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(path_or_url)
                if response.status_code != 200:
                    raise HTTPException(status_code=404, detail="File not found")
                return StreamingResponse(
                    content=response.aiter_bytes(),
                    media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
        except httpx.HTTPError as e:
            logger.exception("Download HTTP error for '%s': %s", filename, e)
            raise HTTPException(status_code=502, detail="Failed to fetch file from storage")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Download failed for '%s': %s", filename, e)
        raise HTTPException(status_code=500, detail="Failed to download file")
