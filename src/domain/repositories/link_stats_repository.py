from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from ..entities.link_stats import LinkStats


class ILinkStatsRepository(ABC):
    @abstractmethod
    async def get_by_link_id(self, link_id: UUID) -> Optional[LinkStats]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_link_ids(self, link_ids: Sequence[UUID]) -> Sequence[LinkStats]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, stats: LinkStats) -> None:
        raise NotImplementedError

    @abstractmethod
    async def increment_click(self, link_id: UUID, used_at: datetime) -> None:
        raise NotImplementedError
