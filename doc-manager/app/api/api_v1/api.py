# app/api/api_v1/api.py
from fastapi import APIRouter

from app.api.api_v1.endpoints import upload, document_settings, document  # split imports

api_router = APIRouter()

# Mount each router at correct logical prefixes
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
#api_router.include_router(process.router, prefix="/process", tags=["Processing"])
#api_router.include_router(status.router, prefix="/status", tags=["Status"])
#api_router.include_router(sample.router, prefix="/trial", tags=["Trial"])
api_router.include_router(document.router, tags=["Documents"])  # defines /documents, /download, DELETE /documents
api_router.include_router(document_settings.router, tags=["Documents"])  # defines /documents/options
