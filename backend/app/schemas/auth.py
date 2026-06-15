"""Pydantic schemas for auth endpoints."""
import re

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: str = ""
    phone: str = ""
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v:
            # Basic email format check (EmailStr handles full validation)
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("邮箱格式不正确")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if v:
            # Chinese mobile: 1[3-9]xxxxxxxxx
            if not re.match(r"^1[3-9]\d{9}$", v):
                raise ValueError("手机号格式不正确，请输入11位中国大陆手机号")
        return v


class LoginRequest(BaseModel):
    account: str  # email or phone
    password: str


class UpdateProfileRequest(BaseModel):
    nickname: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str = ""
    phone: str = ""
    nickname: str = ""
