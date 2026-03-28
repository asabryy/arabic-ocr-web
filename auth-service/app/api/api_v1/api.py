# auth-service/app/api/api_v1/api.py

from fastapi import APIRouter

from app.api.api_v1.endpoints.google_auth import router as google_auth_router
from app.api.api_v1.endpoints.health import router as health_router
from app.api.api_v1.endpoints.login import router as login_router
from app.api.api_v1.endpoints.password import router as password_router
from app.api.api_v1.endpoints.refresh import router as refresh_router
from app.api.api_v1.endpoints.register import router as register_router
from app.api.api_v1.endpoints.users import router as users_router
from app.api.api_v1.endpoints.verify import router as verify_router

api_router = APIRouter()

api_router.include_router(register_router, prefix="/register",       tags=["Auth"])
api_router.include_router(login_router,    prefix="/token",          tags=["Auth"])
api_router.include_router(refresh_router,  prefix="/refresh",        tags=["Auth"])
api_router.include_router(verify_router,   prefix="/verify-email",   tags=["Auth"])
api_router.include_router(password_router, prefix="",                tags=["Auth"])
api_router.include_router(google_auth_router, prefix="/auth/google",  tags=["Auth"])
api_router.include_router(health_router,      prefix="/health",        tags=["Health"])
api_router.include_router(users_router,    prefix="/users",          tags=["Auth"])
