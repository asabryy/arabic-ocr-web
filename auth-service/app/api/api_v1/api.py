# auth-service/app/api/api_v1/api.py

from fastapi import APIRouter

from app.api.api_v1.endpoints.register import router as register_router
from app.api.api_v1.endpoints.login import router as login_router
from app.api.api_v1.endpoints.verify import router as verify_router
from app.api.api_v1.endpoints.health import router as health_router
from app.api.api_v1.endpoints.users import router as users_router

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(register_router, prefix="/register", tags=["Auth"])
api_router.include_router(login_router,    prefix="/token",    tags=["Auth"])
api_router.include_router(verify_router,   prefix="/verify",   tags=["Auth"])

# Health check
api_router.include_router(health_router,   prefix="/health",   tags=["Health"])

# Current‑user endpoint
api_router.include_router(users_router,    prefix="/users",    tags=["Auth"])
