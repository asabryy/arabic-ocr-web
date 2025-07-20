from fastapi import FastAPI
from app.api.api_v1.api import api_router
from app.db.session import engine
from app.db.base import Base
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
import time
import logging
from sqlalchemy import text

load_dotenv()

app = FastAPI(title="Auth Service")

# Include routes early (FastAPI allows this — they're ready before startup events)
app.include_router(api_router, prefix="/api/auth")

# Log routes for debug visibility
for route in app.routes:
    methods = getattr(route, "methods", None)
    print(f"{methods or ''} → {route.path}")

@app.on_event("startup")
async def startup_event():
    """Wait for DB to be ready and create tables."""
    max_retries = 10
    retry_delay = 3

    for attempt in range(max_retries):
        print("Attempting DB connection...")
        try:
            # Simple health check
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection established.")

            # Optional: auto-create tables (disable in production if using Alembic)
            Base.metadata.create_all(bind=engine)
            print("Tables created (if they didn't exist).")
            break
        except OperationalError as e:
            print(f" Attempt {attempt + 1}: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    else:
        print("Failed to connect to the database after multiple attempts.")
        raise SystemExit(1)
