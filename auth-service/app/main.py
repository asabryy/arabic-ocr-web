from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.rate_limit import limiter 
from app.api.api_v1.api import api_router
from app.db.session import engine
from app.db.base import Base
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(api_router, prefix="/api/v1")
