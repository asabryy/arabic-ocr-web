import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.rate_limit import limiter as rate_limiter
from app.db.session import engine

logger = logging.getLogger("auth-service")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB connectivity with retries
    max_retries = 10
    retry_delay = 3
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established on attempt %d", attempt)
            break
        except OperationalError as ex:
            logger.warning("DB connection attempt %d failed: %s", attempt, ex)
            if attempt == max_retries:
                logger.error("Failed to connect to DB after %d attempts", max_retries)
                raise SystemExit(1)
            await asyncio.sleep(retry_delay)
    yield
    logger.info("Auth service shutting down")


app = FastAPI(title="Auth Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = rate_limiter
app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router, prefix="/api/auth/v1")

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait before trying again."},
    )
