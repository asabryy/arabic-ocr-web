# app/api/api_v1/api.py

from fastapi import APIRouter
from app.api.api_v1.endpoints.register import router as register_router
from app.api.api_v1.endpoints.login    import router as token_router
from app.api.api_v1.endpoints.verify   import router as verify_router
from app.api.api_v1.endpoints.health   import router as health_router
from app.api.api_v1.endpoints.users    import router as users_router

api_router = APIRouter()

# mount each service under its own sub‑path
api_router.include_router(register_router, tags=["Auth"])
api_router.include_router(token_router,    tags=["Auth"])
api_router.include_router(verify_router,   tags=["Auth"])
api_router.include_router(health_router,   tags=["Health"])
api_router.include_router(users_router,    tags=["Auth"])
