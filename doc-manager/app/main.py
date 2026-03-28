import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.api_v1.api import api_router
from app.core.config import settings

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/doc-manager/v1")

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
