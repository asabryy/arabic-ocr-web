# app/main.py
from fastapi import FastAPI
from app.api.api_v1.api import api_router
import logging

app = FastAPI(title="Doc Manager Service")

logger = logging.getLogger("doc-manager")

@app.on_event("startup")
def startup_event():
    logger.info("Doc Manager service is starting up...")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Doc Manager service is shutting down...")

app.include_router(api_router, prefix="/api/doc-manager/v1")