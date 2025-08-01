
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentInfo(BaseModel):
    filename: str
    size: int
    last_modified: float