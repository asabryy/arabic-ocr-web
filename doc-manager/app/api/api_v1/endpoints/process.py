from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.queue.task_queue import send_task_to_queue

router = APIRouter()

@router.post("/process")
def process_document(file_id: str = Query(...), mode: str = Query("ocr")):
    if mode not in ["ocr", "layout"]:
        raise HTTPException(status_code=400, detail="Invalid processing mode")

    send_task_to_queue(file_id=file_id, mode=mode)
    return JSONResponse(content={"message": f"Document {file_id} queued for {mode} processing"})
