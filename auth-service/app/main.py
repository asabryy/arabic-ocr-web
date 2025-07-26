import asyncio
import logging

from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware

from app.api.api_v1.api import api_router
from app.core.config import Settings
from app.core.rate_limit import limiter as rate_limiter
from app.db.base import Base
from app.db.session import engine
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

# Load configuration
settings = Settings()

# Configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-service")

# Create FastAPI app
app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://loquacious-syrniki-f7decb.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.state.limiter = rate_limiter
app.add_middleware(SlowAPIMiddleware)

# Mount all API routes under /api/auth/v1
app.include_router(api_router, prefix="/api/auth/v1")


@app.on_event("startup")
async def startup_event():
    """
    On startup, retry database connectivity until successful or until
    max retries are exhausted. In production, use Alembic migrations
    instead of create_all().
    """
    max_retries = 10
    retry_delay = 3
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established on attempt %d", attempt)
            # TODO: Replace with Alembic migrations in production
            # Base.metadata.create_all(bind=engine)
            return
        except OperationalError as ex:
            logger.warning("DB connection attempt %d failed: %s", attempt, ex)
            await asyncio.sleep(retry_delay)

    logger.error("Failed to connect to the database after %d attempts", max_retries)
    raise SystemExit(1)
