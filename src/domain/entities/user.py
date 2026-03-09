import re
from datetime import datetime
from typing import Self
from uuid import UUID

from .base import AggregateRoot

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class User(AggregateRoot):
    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().lower()
        if not _EMAIL_REGEX.match(normalized):
            raise ValueError("Invalid email format")
        return normalized

    @staticmethod
    def validate_password(password: str) -> None:
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

    def __init__(
        self,
        email: str,
        password_hash: str,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> None:
        email = self._normalize_email(email)
        super().__init__(id, created_at)
        self._email = email
        self._password_hash = password_hash

    @property
    def email(self) -> str:
        return self._email

    @property
    def password_hash(self) -> str:
        return self._password_hash


    @classmethod
    def create(cls, email: str, password_hash: str) -> Self:
        email = cls._normalize_email(email)
        if not password_hash:
            raise ValueError("Password hash cannot be empty")
        return cls(email, password_hash)
