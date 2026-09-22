
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    # Reset already enforces 8; registration enforced nothing, so an account could
    # be created with "a" and only strengthened via the reset flow.
    password: str = Field(min_length=8)
    name: str  # Now required at registration

class UserUpdate(BaseModel):
    name: str | None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    email_verified: bool = False
    plan: str = "free"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PlanUpdate(BaseModel):
    plan: Literal["free", "pro"]


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
