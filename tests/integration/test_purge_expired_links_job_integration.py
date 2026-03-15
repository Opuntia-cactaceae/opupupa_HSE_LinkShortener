import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.jobs.purge_expired_links_job import PurgeExpiredLinksJob
from src.infrastructure.db.models.link import LinkModel
from src.infrastructure.db.models.link_stats import LinkStatsModel
from src.infrastructure.cache import LinkCache
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from src.infrastructure.settings import settings


class TestPurgeExpiredLinksJobIntegration:
    """
    Джобу чекаем:
    - батч джобы помечает протухшие ссылки и очищает их кэш;
    - при отсутствии подходящих ссылок кэш не инвалидируется;
    - джоба корректно запускается и останавливается;
    - джоба обрабатывает исключения и продолжает выполнение;
    - батч джобы корректно обрабатывает несколько ссылок за один запуск.
    """

    async def _create_link(
        self,
        db_session: AsyncSession,
        short_code: str,
        original_url: str = "https://example.com/",
        expires_at: Optional[datetime] = None,
        expired_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        owner_user_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        
        link_id = uuid.uuid4()
        link = LinkModel(
            id=link_id,
            short_code=short_code,
            original_url=original_url,
            expires_at=expires_at,
            expired_at=expired_at,
            owner_user_id=owner_user_id,
            is_deleted=False,
        )
        db_session.add(link)
        await db_session.flush()

        stats = LinkStatsModel(
            link_id=link_id,
            clicks=0,
            last_used_at=last_used_at,
        )
        db_session.add(stats)
        await db_session.commit()
        db_session.expire_all()

        return link_id

    async def _get_link_expired_at(
        self,
        db_session: AsyncSession,
        link_id: uuid.UUID,
    ) -> Optional[datetime]:
        
        stmt = select(LinkModel).where(LinkModel.id == link_id)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()
        return link.expired_at if link else None

    async def _cache_key_exists(self, redis_client, short_code: str) -> bool:
        
        key = f"link:code:{short_code}"
        return await redis_client.client.exists(key) == 1

    @pytest.mark.asyncio
    async def test_purge_batch_clears_expired_links_and_invalidates_cache(
        self,
        db_session: AsyncSession,
        redis_client,
        patched_session_factory,
    ):
        
        now = datetime.now(timezone.utc)

        short_code = "expired123"
        original_url = "https://original.url/"
        link_id = await self._create_link(
            db_session,
            short_code=short_code,
            original_url=original_url,
            expires_at=now - timedelta(days=1),
        )

        cache = LinkCache()
        await cache.set(
            short_code=short_code,
            original_url=original_url,
            expires_at=now - timedelta(days=1),
            link_id=link_id,
            ttl_sec=settings.DEFAULT_CACHE_TTL_SEC,
        )
        assert await self._cache_key_exists(redis_client, short_code)

        def uow_factory():
            return SqlAlchemyUnitOfWork()

        job = PurgeExpiredLinksJob(
            uow_factory=uow_factory,
            cache=cache,
            interval_sec=300,
        )

        await job._purge_batch()

        db_session.expire_all()
        expired_at = await self._get_link_expired_at(db_session, link_id)
        assert expired_at is not None

        assert not await self._cache_key_exists(redis_client, short_code)

    @pytest.mark.asyncio
    async def test_purge_batch_no_links_no_cache_invalidation(
        self,
        db_session: AsyncSession,
        redis_client,
        patched_session_factory,
    ):
        
        now = datetime.now(timezone.utc)

        short_code = "active123"
        original_url = "https://active.url/"
        link_id = await self._create_link(
            db_session,
            short_code=short_code,
            original_url=original_url,
            expires_at=now + timedelta(days=1),
        )

        cache = LinkCache()
        await cache.set(
            short_code=short_code,
            original_url=original_url,
            expires_at=now + timedelta(days=1),
            link_id=link_id,
            ttl_sec=settings.DEFAULT_CACHE_TTL_SEC,
        )
        assert await self._cache_key_exists(redis_client, short_code)

        def uow_factory():
            return SqlAlchemyUnitOfWork()

        job = PurgeExpiredLinksJob(
            uow_factory=uow_factory,
            cache=cache,
            interval_sec=300,
        )

        await job._purge_batch()

        db_session.expire_all()
        expired_at = await self._get_link_expired_at(db_session, link_id)
        assert expired_at is None

        assert await self._cache_key_exists(redis_client, short_code)

    @pytest.mark.asyncio
    async def test_job_start_stop(
        self,
        db_session: AsyncSession,
        redis_client,
        patched_session_factory,
    ):
        
        cache = LinkCache()

        def uow_factory():
            return SqlAlchemyUnitOfWork()

        job = PurgeExpiredLinksJob(
            uow_factory=uow_factory,
            cache=cache,
            interval_sec=0.1,
        )

        purge_calls = []
        original_purge = job._purge_batch

        async def mock_purge():
            purge_calls.append(1)
            await original_purge()

        with patch.object(job, "_purge_batch", side_effect=mock_purge):
            await job.start()
            await asyncio.sleep(0.3)
            await job.stop()

        assert job._task is None
        assert len(purge_calls) >= 1

        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_job_handles_exceptions(
        self,
        db_session: AsyncSession,
        redis_client,
        patched_session_factory,
    ):
        
        cache = LinkCache()
        def uow_factory():
            return SqlAlchemyUnitOfWork()

        job = PurgeExpiredLinksJob(
            uow_factory=uow_factory,
            cache=cache,
            interval_sec=0.1,
        )
        call_count = 0

        async def failing_purge():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated purge error")
            

        with patch.object(job, "_purge_batch", side_effect=failing_purge):
            with patch("src.infrastructure.jobs.purge_expired_links_job.logger") as mock_logger:
                await job.start()
                await asyncio.sleep(0.3)
                await job.stop()

                mock_logger.exception.assert_called_once()
                assert "Error in purge job" in mock_logger.exception.call_args[0][0]

        assert job._task is None
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_job_purges_multiple_links_and_invalidates_cache(
        self,
        db_session: AsyncSession,
        redis_client,
        patched_session_factory,
    ):
        
        now = datetime.now(timezone.utc)

        link_data = []
        cache = LinkCache()

        for i in range(3):
            short_code = f"expired{i}"
            original_url = f"https://link{i}.com/"
            expires_at = now - timedelta(days=i + 1)

            link_id = await self._create_link(
                db_session,
                short_code=short_code,
                original_url=original_url,
                expires_at=expires_at,
            )
            link_data.append((link_id, short_code))

            await cache.set(
                short_code=short_code,
                original_url=original_url,
                expires_at=expires_at,
                link_id=link_id,
                ttl_sec=settings.DEFAULT_CACHE_TTL_SEC,
            )
            assert await self._cache_key_exists(redis_client, short_code)

        def uow_factory():
            return SqlAlchemyUnitOfWork()

        job = PurgeExpiredLinksJob(
            uow_factory=uow_factory,
            cache=cache,
            interval_sec=300,
        )

        await job._purge_batch()

        db_session.expire_all()
        for link_id, short_code in link_data:
            expired_at = await self._get_link_expired_at(db_session, link_id)
            assert expired_at is not None

        for link_id, short_code in link_data:
            assert not await self._cache_key_exists(redis_client, short_code)