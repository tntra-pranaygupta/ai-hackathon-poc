import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

# Simple RFC5322-ish email pattern — avoids adding the email-validator
# dependency (not listed in plan.md's requirements.txt) while still
# rejecting obviously malformed addresses per FR-003.
_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _normalize_email(value: str) -> str:
    # fullmatch (not match+"$") so a trailing newline can't sneak past the
    # "$" end-of-string anchor, which in Python also matches just before a
    # trailing "\n".
    if not re.fullmatch(_EMAIL_PATTERN, value):
        raise ValueError("invalid email format")
    # Normalize case so "User@Example.com" and "user@example.com" are
    # treated as the same account for both uniqueness and login.
    return value.lower()


class UserCreate(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        length = len(value.encode("utf-8"))
        if length < 8:
            raise ValueError("password must be at least 8 bytes long")
        if length > 72:
            raise ValueError("password must be at most 72 bytes long")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
