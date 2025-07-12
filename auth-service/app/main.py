from fastapi import FastAPI
from app.api.api_v1.api import api_router
from app.db.session import engine
from app.db.base import Base
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from starlette.requests import Request

limiter = Limiter(key_func=get_remote_address)

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service")
app.include_router(api_router, prefix="/api/v1")
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
