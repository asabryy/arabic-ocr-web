from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from app.services.ocr import run_ocr_pipeline
from app.core.config import UPLOAD_DIR, OUTPUT_DIR
import os

router = APIRouter()

@router.post("/ocr")
async def upload_pdf(file: UploadFile = File(...)):
    docx_filename = await run_ocr_pipeline(file)
    return {"message": "OCR complete", "docx_path": f"/download/{docx_filename}"}

@router.get("/download/{filename}")
def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    return FileResponse(path, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', filename=filename)
