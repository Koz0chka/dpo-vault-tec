"""
Pydantic-схемы валидации входных данных.

Названия полей совпадают с тем, что шлёт фронтенд.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


USERNAME_RE = r"^[A-Za-z0-9_\-]{3,32}$"


class RegisterRequest(BaseModel):
    username: str = Field(..., pattern=USERNAME_RE)
    master_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("master_password")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Мастер-пароль не может быть пустым")
        return v


class LoginRequest(BaseModel):
    username: str
    master_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class PasswordCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    value: str = Field(..., min_length=1, max_length=4096)


class PasswordRenameRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=128)


class PasswordUpdateValueRequest(BaseModel):
    new_value: str = Field(..., min_length=1, max_length=4096)


class GeneratePasswordRequest(BaseModel):
    length: int = Field(16, ge=4, le=128)
    use_lower: bool = True
    use_upper: bool = True
    use_digits: bool = True
    use_symbols: bool = True
    avoid_ambiguous: bool = False


class PasswordEntry(BaseModel):
    id: int
    name: str
    value: str
    created_at: str
    updated_at: str


class PasswordListItem(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str


class GeneratePasswordResponse(BaseModel):
    password: str
    strength: str


class MessageResponse(BaseModel):
    message: str
