from pydantic import BaseModel


class DocumentInfo(BaseModel):
    filename: str
    size: int
    last_modified: float
    status: str = "pending"
