from fastapi import APIRouter

from app.api.api_v1.endpoints import document, document_settings, health, status, upload

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(document.router, tags=["Documents"])
api_router.include_router(document_settings.router, tags=["Documents"])
api_router.include_router(status.router, tags=["Documents"])
