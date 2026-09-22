from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class FeedbackIn(BaseModel):
    category: Literal["bug", "feedback", "support"]
    message: str = Field(min_length=10, max_length=4000)
    # Required for anonymous senders; ignored when a valid token is present, since the
    # account's own address is more trustworthy than whatever is typed in the form.
    email: EmailStr | None = None
    # Where they were when they hit the problem — the single most useful bug detail.
    page: str | None = Field(default=None, max_length=200)
    # Honeypot: a real browser leaves this empty because the field is hidden.
    website: str | None = Field(default=None, max_length=200)
