import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from uuid import uuid4

from src.domain.entities.link import Link
from src.domain.entities.user import User
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


def make_test_hash(password: str) -> str:
    return f"test_hash_{password}"


class TestExpirationBehaviour:
    """
    Тесты поведения протухших ссылок:
    - протухшая ссылка не выполняет редирект;
    - протухшая ссылка возвращается в списке протухших;
    - кейс помечает протухшие ссылки как протухшие;
    - кейс не затрагивает активные ссылки;
    - давно не использовавшиеся ссылки считаются протухшими;
    - недавно использовавшиеся ссылки не считаются протухшими;
    - после очистки протухшая ссылка больше не выполняет редирект.
    """
    @pytest.mark.asyncio
    async def test_expired_link_cannot_redirect(self, client, uow):
        async with uow:
            password_hash = make_test_hash("testpassword123")
            user = User.create(
                email=f"test_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        short_code = ShortCode("expired123")
        original_url = OriginalUrl("https://expired.example.com")
        expired_at = datetime.now(timezone.utc) - timedelta(days=1)

        async with uow:
            link = Link(
                short_code=short_code,
                original_url=original_url,
                owner_user_id=user.id,
                expires_at=None,
                expired_at=expired_at,
                id=uuid4(),
            )
            await uow.links.add(link)
            await uow.commit()

        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_expired_link_returned_in_expired_list_endpoint(self, client, uow):
        async with uow:
            password_hash = make_test_hash("testpassword123")
            user = User.create(
                email=f"test2_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        short_code = ShortCode("expired456")
        original_url = OriginalUrl("https://expired2.example.com")
        expired_at = datetime.now(timezone.utc) - timedelta(days=1)

        async with uow:
            link = Link(
                short_code=short_code,
                original_url=original_url,
                owner_user_id=user.id,
                expires_at=None,
                expired_at=expired_at,
                id=uuid4(),
            )
            await uow.links.add(link)
            await uow.commit()

        from src.application.use_cases.list_expired_links import ListExpiredLinksUseCase
        async with uow:
            use_case = ListExpiredLinksUseCase(uow)
            items = await use_case.execute(owner_user_id=user.id, page=1, size=10)

        assert len(items) >= 1
        found = any(item.short_code == str(short_code) for item in items)
        assert found, f"Expired link {short_code} not found in list"

    @pytest.mark.asyncio
    async def test_purge_job_processes_expired_links(self, client, uow, test_settings):
        async with uow:
            password_hash = make_test_hash("testpassword123")
            user = User.create(
                email=f"purge_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        short_code = ShortCode("purgeexpired")
        original_url = OriginalUrl("https://purge.example.com")
        expires_at_future = datetime.now(timezone.utc) + timedelta(days=1)
        expires_at_obj = ExpiresAt.from_datetime(expires_at_future)

        async with uow:
            link = Link(
                short_code=short_code,
                original_url=original_url,
                owner_user_id=user.id,
                expires_at=expires_at_obj,
                id=uuid4(),
            )
            await uow.links.add(link)
            await uow.commit()

        async with uow:
            from src.infrastructure.db.models.link import LinkModel
            from sqlalchemy import update
            session = uow._session
            stmt = update(LinkModel).where(LinkModel.id == link.id).values(
                expires_at=datetime.now(timezone.utc) - timedelta(days=1)
            )
            await session.execute(stmt)
            await session.commit()

        async with uow:
            from src.infrastructure.db.models.link import LinkModel
            from sqlalchemy import select
            session = uow._session
            stmt = select(LinkModel).where(LinkModel.id == link.id)
            result = await session.execute(stmt)
            model = result.scalar_one()
            assert model.expired_at is None

        async with uow:
            from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
            from src.application.services.time_provider import SystemTimeProvider
            use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
            purged_links = await use_case.execute()

        assert len(purged_links) == 1
        assert purged_links[0].short_code == short_code
        assert purged_links[0].expired_at is not None

        async with uow:
            from src.infrastructure.db.models.link import LinkModel
            from sqlalchemy import select
            session = uow._session
            stmt = select(LinkModel).where(LinkModel.id == link.id)
            result = await session.execute(stmt)
            model = result.scalar_one()
            assert model.expired_at is not None

    @pytest.mark.asyncio
    async def test_purge_job_ignores_active_links(self, client, uow, test_settings):
        password_hash = make_test_hash("testpassword123")
        user = User.create(
            email=f"active_{uuid4().hex[:8]}@example.com",
            password_hash=password_hash,
        )
        await uow.users.add(user)
        await uow.commit()

        short_code = ShortCode("active123")
        original_url = OriginalUrl("https://active.example.com")
        expires_at = ExpiresAt.from_datetime(
            datetime.now(timezone.utc) + timedelta(days=1)  
        )

        link = Link(
            short_code=short_code,
            original_url=original_url,
            owner_user_id=user.id,
            expires_at=expires_at,
            id=uuid4(),
        )
        await uow.links.add(link)
        await uow.commit()

        async with uow:
            from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
            from src.application.services.time_provider import SystemTimeProvider
            use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
            purged_links = await use_case.execute()

        assert len(purged_links) == 0

        async with uow:
            from src.infrastructure.db.models.link import LinkModel
            from sqlalchemy import select
            session = uow._session
            stmt = select(LinkModel).where(LinkModel.id == link.id)
            result = await session.execute(stmt)
            model = result.scalar_one()
            assert model.expired_at is None

    @pytest.mark.asyncio
    async def test_stale_link_processed_correctly(self, client, uow, test_settings):
        async with uow:
            password_hash = make_test_hash("testpassword123")
            user = User.create(
                email=f"stale_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        short_code = ShortCode("stale123")
        original_url = OriginalUrl("https://stale.example.com")
        expires_at = None

        async with uow:
            link = Link(
                short_code=short_code,
                original_url=original_url,
                owner_user_id=user.id,
                expires_at=expires_at,
                id=uuid4(),
            )
            await uow.links.add(link)
            await uow.commit()

        async with uow:
            from src.infrastructure.db.models.link_stats import LinkStatsModel
            from sqlalchemy import insert, update
            session = uow._session
            stale_threshold = datetime.now(timezone.utc) - timedelta(days=100)
            stmt = insert(LinkStatsModel).values(
                link_id=link.id,
                clicks=0,
                last_used_at=stale_threshold,
            ).prefix_with('OR IGNORE')
            await session.execute(stmt)
            stmt = update(LinkStatsModel).where(LinkStatsModel.link_id == link.id).values(
                last_used_at=stale_threshold
            )
            await session.execute(stmt)
            await session.commit()

        from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
        from src.application.services.time_provider import SystemTimeProvider

        with patch('src.infrastructure.settings.settings') as mock_settings:
            mock_settings.UNUSED_LINK_TTL_DAYS = 90
            async with uow:
                use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
                purged_links = await use_case.execute()

        assert len(purged_links) == 1
        assert purged_links[0].short_code == short_code
        assert purged_links[0].expired_at is not None

        async with uow:
            from src.infrastructure.db.models.link import LinkModel
            from sqlalchemy import select
            session = uow._session
            stmt = select(LinkModel).where(LinkModel.id == link.id)
            result = await session.execute(stmt)
            model = result.scalar_one()
            assert model.expired_at is not None

    @pytest.mark.asyncio
    async def test_stale_link_with_recent_usage_not_processed(self, client, uow, test_settings):
        async with uow:
            password_hash = make_test_hash("testpassword123")
            user = User.create(
                email=f"recent_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        short_code = ShortCode("recent123")
        original_url = OriginalUrl("https://recent.example.com")
        expires_at = None

        async with uow:
            link = Link(
                short_code=short_code,
                original_url=original_url,
                owner_user_id=user.id,
                expires_at=expires_at,
                id=uuid4(),
            )
            await uow.links.add(link)
            await uow.commit()

        async with uow:
            from src.infrastructure.db.models.link_stats import LinkStatsModel
            from sqlalchemy import insert, update
            session = uow._session
            recent = datetime.now(timezone.utc) - timedelta(days=10)
            stmt = insert(LinkStatsModel).values(
                link_id=link.id,
                clicks=0,
                last_used_at=recent,
            ).prefix_with('OR IGNORE')
            await session.execute(stmt)
            stmt = update(LinkStatsModel).where(LinkStatsModel.link_id == link.id).values(
                last_used_at=recent
            )
            await session.execute(stmt)
            await session.commit()

        from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
        from src.application.services.time_provider import SystemTimeProvider

        with patch('src.infrastructure.settings.settings') as mock_settings:
            mock_settings.UNUSED_LINK_TTL_DAYS = 90
            async with uow:
                use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
                purged_links = await use_case.execute()

        assert len(purged_links) == 0

        async with uow:
            link = await uow.links.get_by_short_code(str(short_code))
            assert link.expired_at is None

    @pytest.mark.asyncio
    async def test_purged_expired_link_cannot_redirect(self, client, uow):
        async with uow:
            password_hash = make_test_hash("testpassword123")
            user = User.create(
                email=f"purgeredirect_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        short_code = ShortCode("purgeredir")
        original_url = OriginalUrl("https://purgeredir.example.com")

        async with uow:
            link = Link(
                short_code=short_code,
                original_url=original_url,
                owner_user_id=user.id,
                expires_at=ExpiresAt.from_datetime(datetime.now(timezone.utc) - timedelta(days=1)),
                id=uuid4(),
            )
            await uow.links.add(link)
            await uow.commit()

        async with uow:
            from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
            from src.application.services.time_provider import SystemTimeProvider

            use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
            purged_links = await use_case.execute()

        assert len(purged_links) == 1
        assert purged_links[0].short_code == short_code

        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)
        assert response.status_code == 404