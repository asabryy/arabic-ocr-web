from fastapi import APIRouter
from app.api.api_v1.endpoints import upload, process, status, sample

api_router = APIRouter()
api_router.include_router(upload.router, prefix="/docs", tags=["Documents"])
api_router.include_router(process.router, prefix="/docs", tags=["Documents"])
api_router.include_router(status.router, prefix="/docs", tags=["Documents"])
api_router.include_router(sample.router, prefix="/trial", tags=["Trial"])


# Now update main.py accordingly (just for context)
# app/main.py
...
from app.api.api_v1.api import api_router
...
app.include_router(api_router, prefix="/api/doc-manager/v1")