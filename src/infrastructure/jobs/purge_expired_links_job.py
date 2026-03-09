import asyncio
import logging
from typing import Optional

from ...application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
from ..cache import LinkCache
from ..db import SqlAlchemyUnitOfWork
from ...application.services.time_provider import SystemTimeProvider

logger = logging.getLogger(__name__)


class PurgeExpiredLinksJob:
    def __init__(
        self,
        uow_factory: callable,
        cache: LinkCache,
        interval_sec: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._cache = cache
        self._interval_sec = interval_sec
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        logger.info("PurgeExpiredLinksJob started")
        while not self._stop_event.is_set():
            try:
                await self._purge_batch()
            except Exception as e:
                logger.exception("Error in purge job: %s", e)
            await asyncio.sleep(self._interval_sec)
        logger.info("PurgeExpiredLinksJob stopped")

    async def _purge_batch(self) -> None:
        async with self._uow_factory() as uow:
            use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
            purged_links = await use_case.execute()
            if purged_links:
                logger.info("Purged %d expired links", len(purged_links))
                for link in purged_links:
                    await self._cache.invalidate(str(link.short_code))