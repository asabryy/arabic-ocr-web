# app/main.py
import logging
from fastapi import FastAPI
from app.api.api_v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("doc-manager")

app = FastAPI(title="Doc Manager Service")

@app.on_event("startup")
def startup_event():
    logger.info("Doc Manager service is starting up...")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Doc Manager service is shutting down...")

app.include_router(api_router, prefix="/api/doc-manager/v1")
