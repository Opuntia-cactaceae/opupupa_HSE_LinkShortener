from datetime import timedelta
from typing import Sequence

from ...domain.entities.link import Link
from ..services.time_provider import TimeProvider
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.settings import settings


class PurgeExpiredLinksUseCase:
    def __init__(self, uow: IUnitOfWork, time_provider: TimeProvider) -> None:
        self._uow = uow
        self._time_provider = time_provider

    async def execute(self, batch_size: int = 1000) -> Sequence[Link]:
        now = self._time_provider.now()
        expired_links = await self._uow.links.list_expired(now, batch_size)

        stale_threshold = now - timedelta(days=settings.UNUSED_LINK_TTL_DAYS)
        stale_links = await self._uow.links.find_stale_links(stale_threshold, batch_size)

        processed_ids = set()
        purged_links: list[Link] = []

        for link in list(expired_links) + list(stale_links):
            if link.id in processed_ids:
                continue
            processed_ids.add(link.id)

            link.mark_expired(now)
            await self._uow.links.update(link)
            purged_links.append(link)

        await self._uow.commit()
        return purged_links