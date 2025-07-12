from fastapi import APIRouter
from app.api.api_v1.endpoints import login, register

api_router = APIRouter()
api_router.include_router(register.router, prefix="", tags=["register"])
api_router.include_router(login.router,    prefix="", tags=["login"])