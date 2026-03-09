from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from ..entities.link import Link


class ILinkRepository(ABC):
    @abstractmethod
    async def get_by_short_code(self, code: str) -> Optional[Link]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Link]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_original_url(
        self, url: str, limit: int = 100, offset: int = 0
    ) -> Sequence[Link]:
        raise NotImplementedError

    @abstractmethod
    async def exists_short_code(self, code: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add(self, link: Link) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, link: Link) -> None:
        raise NotImplementedError


    @abstractmethod
    async def list_expired(self, now: datetime, limit: int = 1000) -> Sequence[Link]:
        raise NotImplementedError

    @abstractmethod
    async def list_expired_history(
        self, owner_user_id: Optional[UUID], limit: int = 100, offset: int = 0
    ) -> Sequence[Link]:
        raise NotImplementedError

    @abstractmethod
    async def find_stale_links(
        self, stale_threshold: datetime, limit: int = 1000
    ) -> Sequence[Link]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_project_id(
        self, project_id: UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[Link]:
        raise NotImplementedError
