from fastapi import APIRouter
from app.api.api_v1.endpoints import register, login, verify

api_router = APIRouter()
api_router.include_router(register.router, tags=["Register"])
api_router.include_router(login.router, tags=["Login"])
api_router.include_router(verify.router, tags=["Verify Email"])