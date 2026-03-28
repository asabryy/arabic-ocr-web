import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.queue.task_queue import send_task_to_queue

router = APIRouter()

SAMPLE_DIR = "sample_docs"
os.makedirs(SAMPLE_DIR, exist_ok=True)

@router.post("/sample")
async def sample_upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    filename = f"sample_{uuid4()}_{file.filename}"
    filepath = os.path.join(SAMPLE_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Add to RabbitMQ queue with "trial" mode
    send_task_to_queue(file_id=filename, mode="trial")

    return JSONResponse(content={"message": "Sample file received and queued", "file_id": filename})
