
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
    # "unlimited" is the comped/beta tier — granted by hand, never sold, no Stripe
    # subscription behind it. Keep in step with quota.limits_for() in doc-manager:
    # a plan value that function does not recognise silently falls back to free.
    plan: Literal["free", "pro", "unlimited"]
    # Tell the account holder. Off by default so bulk or corrective changes stay quiet.
    notify: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
