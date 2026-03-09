from datetime import datetime
from typing import Optional, Self
from uuid import UUID

from .base import AggregateRoot


class Project(AggregateRoot):
    def __init__(
        self,
        name: str,
        owner_user_id: UUID,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id, created_at)
        self._name = self._validate_name(name)
        self._owner_user_id = owner_user_id
        self._updated_at = updated_at or datetime.now()

    @property
    def name(self) -> str:
        return self._name

    @property
    def owner_user_id(self) -> UUID:
        return self._owner_user_id

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update_name(self, new_name: str) -> None:
        self._name = self._validate_name(new_name)
        self._updated_at = datetime.now()

    def is_owner(self, user_id: Optional[UUID]) -> bool:
        return self._owner_user_id == user_id

    @staticmethod
    def _validate_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Project name cannot be empty")
        if len(name) > 100:
            raise ValueError("Project name cannot exceed 100 characters")
        return name

    @classmethod
    def create(cls, name: str, owner_user_id: UUID) -> Self:
        return cls(name, owner_user_id)