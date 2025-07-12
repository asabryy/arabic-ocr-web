from fastapi import FastAPI
from app.api.api_v1.api import api_router
from app.db.session import engine
from app.db.base import Base
import os
from dotenv import load_dotenv

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service")
app.include_router(api_router, prefix="/api/v1")
