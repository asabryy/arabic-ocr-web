import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger("auth-service.health")


@router.get(
    "",
    summary="Service health check",
)
def health_check(
    db: Session = Depends(get_db),
):
    """
    Verify that the database connection is healthy.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as ex:
        logger.error("Health check failed: %s", ex)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connectivity issue",
        )
