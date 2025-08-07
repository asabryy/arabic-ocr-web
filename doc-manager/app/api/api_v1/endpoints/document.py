import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
import httpx

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
async def download_file(
    user_id: str = Query(...),
    filename: str = Query(...),
    preview: bool = Query(False),
    storage: FileStorage = Depends(get_storage),
):
    logger.info(f"⬇️ [GET /download] Request to download '{filename}' for user_id={user_id}")

    try:
        signed_url = storage.get_path(user_id, filename)

        if preview:
            async with httpx.AsyncClient() as client:
                response = await client.get(signed_url)

                if response.status_code != 200:
                    logger.error(f"Failed to fetch PDF: {response.status_code} {response.text}")
                    raise HTTPException(status_code=404, detail="PDF not found or access denied.")

                content_type = response.headers.get("Content-Type", "")
                if "application/pdf" not in content_type:
                    logger.error(f"Invalid content type for preview: {content_type}")
                    raise HTTPException(status_code=400, detail="Preview failed, invalid PDF.")

                return StreamingResponse(
                    content=await response.aread(),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"inline; filename={filename}",
                        "Access-Control-Allow-Origin": "*",
                    },
                )

        # Allow direct download
        return RedirectResponse(signed_url)

    except Exception as e:
        logger.exception(f"Download failed for {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file.")
