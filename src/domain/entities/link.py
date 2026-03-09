from datetime import datetime, timezone
from typing import Optional, Self
from uuid import UUID

from ..value_objects.expires_at import ExpiresAt
from ..value_objects.original_url import OriginalUrl
from ..value_objects.short_code import ShortCode
from .base import AggregateRoot


class Link(AggregateRoot):
    def __init__(
        self,
        short_code: ShortCode,
        original_url: OriginalUrl,
        owner_user_id: Optional[UUID],
        expires_at: Optional[ExpiresAt] = None,
        project_id: Optional[UUID] = None,
        expired_at: Optional[datetime] = None,
        is_deleted: bool = False,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id, created_at)
        self._short_code = short_code
        self._original_url = original_url
        self._owner_user_id = owner_user_id
        self._expires_at = expires_at
        self._project_id = project_id
        self._expired_at = expired_at
        self._is_deleted = is_deleted
        self._updated_at = updated_at or datetime.now()

    @property
    def short_code(self) -> ShortCode:
        return self._short_code

    @property
    def original_url(self) -> OriginalUrl:
        return self._original_url

    @property
    def owner_user_id(self) -> Optional[UUID]:
        return self._owner_user_id

    @property
    def project_id(self) -> Optional[UUID]:
        return self._project_id

    @property
    def expires_at(self) -> Optional[ExpiresAt]:
        return self._expires_at

    @property
    def expired_at(self) -> Optional[datetime]:
        return self._expired_at

    @property
    def is_deleted(self) -> bool:
        return self._is_deleted

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def is_expired(self, when: datetime) -> bool:
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if self._expired_at is not None:
            return True
        if self._expires_at is None:
            return False
        return self._expires_at.is_expired(when)

    def is_available(self, when: datetime) -> bool:
        return not self._is_deleted and not self.is_expired(when)

    def update_original_url(self, new_url: OriginalUrl) -> None:
        self._original_url = new_url
        self._updated_at = datetime.now()

    def update_short_code(self, new_short_code: ShortCode) -> None:
        self._short_code = new_short_code
        self._updated_at = datetime.now()

    def update_expires_at(self, new_expires_at: Optional[ExpiresAt]) -> None:
        self._expires_at = new_expires_at
        self._updated_at = datetime.now()

    def update_project_id(self, new_project_id: Optional[UUID]) -> None:
        self._project_id = new_project_id
        self._updated_at = datetime.now()

    def mark_expired(self, when: datetime) -> None:
        self._expired_at = when
        self._updated_at = datetime.now()

    def is_owner(self, user_id: Optional[UUID]) -> bool:
        return self._owner_user_id == user_id

    def delete(self) -> None:
        self._is_deleted = True
        self._updated_at = datetime.now()

    def restore(self) -> None:
        self._is_deleted = False
        self._updated_at = datetime.now()

    @classmethod
    def create(
        cls,
        short_code: ShortCode,
        original_url: OriginalUrl,
        owner_user_id: Optional[UUID] = None,
        expires_at: Optional[ExpiresAt] = None,
        project_id: Optional[UUID] = None,
    ) -> Self:
        return cls(
            short_code=short_code,
            original_url=original_url,
            owner_user_id=owner_user_id,
            expires_at=expires_at,
            project_id=project_id,
        )
