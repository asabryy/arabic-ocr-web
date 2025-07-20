from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.db.session import SessionLocal 
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
def health_check():
    print("Entering health_check...")

    try:
        db: Session = SessionLocal()
        print("Running SELECT 1...")
        db.execute(text("SELECT 1"))
        print("SELECT 1 succeeded.")
        return {"status": "ok"}
    except Exception as e:
        print(f"Health check DB error: {e}")
        return {"status": "error", "detail": str(e)}
    finally:
        db.close()
        print("Closed DB session.")
