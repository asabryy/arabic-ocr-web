
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str  # Now required at registration

class UserUpdate(BaseModel):
    name: str | None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    email_verified: bool = False

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
