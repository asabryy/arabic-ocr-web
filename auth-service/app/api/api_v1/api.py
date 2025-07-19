from fastapi import APIRouter
from app.api.api_v1.endpoints.register import router as register_router
from app.api.api_v1.endpoints.login import router as login_router
from app.api.api_v1.endpoints.verify import router as verify_router
from app.api.api_v1.endpoints.health import router as health_router

api_router = APIRouter()
api_router.include_router(register_router, tags=["Register"])
api_router.include_router(login_router, tags=["Login"])
api_router.include_router(verify_router, tags=["Verify Email"])
api_router.include_router(health_router, tags=["Health"])
