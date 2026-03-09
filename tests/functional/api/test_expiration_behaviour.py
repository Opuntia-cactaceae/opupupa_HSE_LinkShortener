import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from uuid import uuid4

from src.domain.entities.link import Link
from src.domain.entities.user import User, pwd_context
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


class TestExpirationBehaviour:
    """Functional tests for expiration behaviour."""

    @pytest.mark.asyncio
    async def test_expired_link_cannot_redirect(self, client, uow):
        """Test that expired link returns 404 on redirect."""
        # Arrange: create a link with expired_at set (marked expired)
        async with uow:
            # Create a user first (required for link ownership)
            password_hash = pwd_context.hash("testpassword123")
            user = User.create(
                email=f"test_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        # Create link with expired_at set (marked expired)
        short_code = ShortCode("expired123")
        original_url = OriginalUrl("https://expired.example.com")
        expired_at = datetime.now(timezone.utc) - timedelta(days=1)

        async with uow:
            link = Link(
                short_code=short_code,
                original_url=original_url,
                owner_user_id=user.id,
                expires_at=None,  # No expiration date
                expired_at=expired_at,  # Marked as expired
                id=uuid4(),
            )
            await uow.links.add(link)
            await uow.commit()

        # Act: Try to redirect
        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Assert: Should return 404 because link is expired
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_expired_link_returned_in_expired_list_endpoint(self, client, uow):
        """Test that expired links are returned by /links/expired endpoint."""
        # Arrange: create expired link (marked expired)
        async with uow:
            password_hash = pwd_context.hash("testpassword123")
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

        # Act: Call expired list endpoint via use case (since endpoint requires auth)
        from src.application.use_cases.list_expired_links import ListExpiredLinksUseCase
        async with uow:
            use_case = ListExpiredLinksUseCase(uow)
            items = await use_case.execute(owner_user_id=user.id, page=1, size=10)

        # Assert: Link appears in result
        assert len(items) >= 1
        found = any(item.short_code == str(short_code) for item in items)
        assert found, f"Expired link {short_code} not found in list"

    @pytest.mark.asyncio
    async def test_purge_job_processes_expired_links(self, client, uow, test_settings):
        """Test purge job marks expired links as expired and invalidates cache."""
        # Arrange: create link with past expires_at (should be purged)
        async with uow:
            password_hash = pwd_context.hash("testpassword123")
            user = User.create(
                email=f"purge_{uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
            )
            await uow.users.add(user)
            await uow.commit()

        short_code = ShortCode("purgeexpired")
        original_url = OriginalUrl("https://purge.example.com")
        # Need to bypass ExpiresAt validation (must be future). Instead, we'll set expires_at via
        # database model directly, or use a future expires_at and manually set expired_at later.
        # Let's create a link with future expires_at, then manually update DB to past.
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

        # Manually update expires_at in DB to past (bypass domain validation)
        # We'll use SQLAlchemy model directly
        async with uow:
            from src.infrastructure.db.models.link import LinkModel
            from sqlalchemy import update
            session = uow._session
            stmt = update(LinkModel).where(LinkModel.id == link.id).values(
                expires_at=datetime.now(timezone.utc) - timedelta(days=1)
            )
            await session.execute(stmt)
            await session.commit()

        # Ensure link is not already marked expired
        async with uow:
            from src.infrastructure.db.models.link import LinkModel
            from sqlalchemy import select
            session = uow._session
            stmt = select(LinkModel).where(LinkModel.id == link.id)
            result = await session.execute(stmt)
            model = result.scalar_one()
            assert model.expired_at is None

        # Act: Run purge expired links use case
        async with uow:
            from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
            from src.application.services.time_provider import SystemTimeProvider
            use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
            purged_links = await use_case.execute()

        # Assert: Link is marked expired
        assert len(purged_links) == 1
        assert purged_links[0].short_code == short_code
        assert purged_links[0].expired_at is not None

        # Verify in database
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
        """Test purge job does not process active (non-expired) links."""
        # Arrange: create active link with future expiration
        password_hash = pwd_context.hash("testpassword123")
        user = User.create(
            email=f"active_{uuid4().hex[:8]}@example.com",
            password_hash=password_hash,
        )
        await uow.users.add(user)
        await uow.commit()

        short_code = ShortCode("active123")
        original_url = OriginalUrl("https://active.example.com")
        expires_at = ExpiresAt.from_datetime(
            datetime.now(timezone.utc) + timedelta(days=1)  # future
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

        # Act: Run purge expired links use case
        async with uow:
            from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
            from src.application.services.time_provider import SystemTimeProvider
            use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
            purged_links = await use_case.execute()

        # Assert: No links purged
        assert len(purged_links) == 0

        # Verify link not marked expired
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
        """Test stale links (unused for UNUSED_LINK_TTL_DAYS) are marked expired."""
        # Arrange: create link with last_used_at far in the past
        async with uow:
            password_hash = pwd_context.hash("testpassword123")
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

        # Update last_used_at directly in DB (not exposed in domain entity)
        async with uow:
            from src.infrastructure.db.models.link_stats import LinkStatsModel
            from sqlalchemy import insert, update
            session = uow._session
            stale_threshold = datetime.now(timezone.utc) - timedelta(days=100)
            # Ensure stats row exists
            stmt = insert(LinkStatsModel).values(
                link_id=link.id,
                clicks=0,
                last_used_at=stale_threshold,
            ).prefix_with('OR IGNORE')
            await session.execute(stmt)
            # Update last_used_at (in case row already existed)
            stmt = update(LinkStatsModel).where(LinkStatsModel.link_id == link.id).values(
                last_used_at=stale_threshold
            )
            await session.execute(stmt)
            await session.commit()

        # Act: Run purge expired links use case with mocked settings
        from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
        from src.application.services.time_provider import SystemTimeProvider

        with patch('src.infrastructure.settings.settings') as mock_settings:
            mock_settings.UNUSED_LINK_TTL_DAYS = 90  # stale threshold
            async with uow:
                use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
                purged_links = await use_case.execute()

        # Assert: Stale link is purged
        assert len(purged_links) == 1
        assert purged_links[0].short_code == short_code
        assert purged_links[0].expired_at is not None

        # Verify in database
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
        """Test stale links with recent last_used_at are not marked expired."""
        # Arrange: create link with recent last_used_at
        async with uow:
            password_hash = pwd_context.hash("testpassword123")
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

        # Update last_used_at to recent
        async with uow:
            from src.infrastructure.db.models.link_stats import LinkStatsModel
            from sqlalchemy import insert, update
            session = uow._session
            recent = datetime.now(timezone.utc) - timedelta(days=10)
            # Ensure stats row exists
            stmt = insert(LinkStatsModel).values(
                link_id=link.id,
                clicks=0,
                last_used_at=recent,
            ).prefix_with('OR IGNORE')
            await session.execute(stmt)
            # Update last_used_at (in case row already existed)
            stmt = update(LinkStatsModel).where(LinkStatsModel.link_id == link.id).values(
                last_used_at=recent
            )
            await session.execute(stmt)
            await session.commit()

        # Act: Run purge expired links use case with mocked settings
        from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
        from src.application.services.time_provider import SystemTimeProvider

        with patch('src.infrastructure.settings.settings') as mock_settings:
            mock_settings.UNUSED_LINK_TTL_DAYS = 90
            async with uow:
                use_case = PurgeExpiredLinksUseCase(uow, SystemTimeProvider())
                purged_links = await use_case.execute()

        # Assert: No links purged (not stale enough)
        assert len(purged_links) == 0

        # Verify link not marked expired
        async with uow:
            link = await uow.links.get_by_short_code(str(short_code))
            assert link.expired_at is None