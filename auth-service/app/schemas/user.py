from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str  # Now required at registration

class UserUpdate(BaseModel):
    name: Optional[str]

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None  # Return name in API responses

    model_config = {
        "from_attributes": True
    }

class Token(BaseModel):
    access_token: str
    token_type: str
