from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class RegisterUserRequest:
    email: str
    password: str


@dataclass
class RegisterUserResponse:
    user_id: UUID


@dataclass
class LoginUserRequest:
    email: str
    password: str


@dataclass
class AuthResponse:
    access_token: str
    token_type: str = "bearer"