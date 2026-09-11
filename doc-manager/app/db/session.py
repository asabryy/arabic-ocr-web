"""Engine for the Postgres shared with auth-service.

doc-manager does not own this schema (auth-service does, via Alembic); it only reads
`users.plan` and reads/writes `usage_daily`. Exposed as a FastAPI dependency so tests
can override it with a test engine.
"""

from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import Engine, create_engine

from app.core.config import settings


@lru_cache(maxsize=1)
def _build_engine() -> Engine:
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )


def get_engine() -> Engine:
    if not settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quota database not configured",
        )
    return _build_engine()
