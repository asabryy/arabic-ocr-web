from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
import shutil
import os
from app.queue.task_queue import send_task_to_queue

router = APIRouter()

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    filename = f"{uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    send_task_to_queue(file_id=filename, mode="ocr")

    return JSONResponse(content={"message": "File uploaded and queued", "file_id": filename})

@router.post("/test")
async def test_demo_conversion():
    sample_file_id = "demo_page_sample.pdf"
    send_task_to_queue(file_id=sample_file_id, mode="ocr")

    return JSONResponse(content={"message": "Test job submitted", "file_id": sample_file_id})
