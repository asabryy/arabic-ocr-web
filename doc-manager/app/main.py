import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.rate_limit import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("doc-manager")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Doc Manager service starting up...")
    yield
    logger.info("Doc Manager service shutting down...")


app = FastAPI(title="Doc Manager Service", lifespan=lifespan)

# Decorator-based rate limits only (used by the anonymous trial); no default limits.
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": {
                "code": "trial_limit_exceeded",
                "message": "Trial limit reached. Create a free account to keep converting.",
                "limit": settings.TRIAL_RATE_LIMIT,
            }
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/doc-manager/v1")

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
