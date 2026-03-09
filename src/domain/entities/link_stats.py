from datetime import datetime
from typing import Self
from uuid import UUID

from .base import Entity


class LinkStats(Entity[UUID]):
    def __init__(
        self,
        link_id: UUID,
        clicks: int = 0,
        last_used_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(link_id, created_at or datetime.now())
        self._clicks = clicks
        self._last_used_at = last_used_at

    @property
    def link_id(self) -> UUID:
        return self._id

    @property
    def clicks(self) -> int:
        return self._clicks

    @property
    def last_used_at(self) -> datetime | None:
        return self._last_used_at

    def record_click(self, used_at: datetime) -> None:
        self._clicks += 1
        self._last_used_at = used_at

    @classmethod
    def create(cls, link_id: UUID) -> Self:
        return cls(link_id)
