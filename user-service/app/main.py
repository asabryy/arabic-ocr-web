from fastapi import FastAPI
from app.api import routes
from app.core.config import settings

app = FastAPI(title="User Service")
app.include_router(routes.router, prefix="/api")