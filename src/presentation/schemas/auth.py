import re
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    model_config = {
        "extra": "forbid",
    }


class RegisterResponse(BaseModel):
    user_id: str

    @classmethod
    def from_dto(cls, dto):
        return cls(user_id=str(dto.user_id))


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    model_config = {
        "extra": "forbid",
    }


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    @classmethod
    def from_dto(cls, dto):
        return cls(access_token=dto.access_token, token_type=dto.token_type)