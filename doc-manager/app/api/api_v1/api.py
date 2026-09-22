from fastapi import APIRouter

from app.api.api_v1.endpoints import document, health, status, trial, upload

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(trial.router, prefix="/trial", tags=["Trial"])
api_router.include_router(document.router, tags=["Documents"])
api_router.include_router(status.router, tags=["Documents"])
