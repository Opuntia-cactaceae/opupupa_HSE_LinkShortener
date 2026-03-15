import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link import LinkModel
from src.infrastructure.db.models.link_stats import LinkStatsModel
from src.infrastructure.settings import settings


class TestLinkResolution:
    

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        
        unique_email = f"redirectuser_{uuid.uuid4().hex[:8]}@example.com"

        response = await client.post(
            "/auth/register",
            json={"email": unique_email, "password": "password"},
        )
        assert response.status_code == 201

        response = await client.post(
            "/auth/login",
            json={"email": unique_email, "password": "password"},
        )
        assert response.status_code == 200

        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_redirect_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com"},
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        original_url = data["original_url"]

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}"
        )
        assert redirect_response.status_code == 307
        assert "Location" in redirect_response.headers
        assert redirect_response.headers["Location"] == original_url

        stmt = select(LinkStatsModel).join(LinkModel).where(
            LinkModel.short_code == short_code
        )
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()
        assert stats is not None
        assert stats.clicks == 1
        assert stats.last_used_at is not None

    @pytest.mark.asyncio
    async def test_redirect_increments_stats(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.org"},
        )
        assert create_response.status_code == 201

        short_code = create_response.json()["short_code"]

        stmt = select(LinkStatsModel).join(LinkModel).where(
            LinkModel.short_code == short_code
        )
        result = await db_session.execute(stmt)
        stats_before = result.scalar_one_or_none()
        assert stats_before is not None
        assert stats_before.clicks == 0

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}"
        )
        assert redirect_response.status_code == 307

        db_session.expire_all()
        result = await db_session.execute(stmt)
        stats_after = result.scalar_one_or_none()
        assert stats_after is not None
        assert stats_after.clicks == 1

    @pytest.mark.asyncio
    async def test_redirect_updates_last_used_at(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.net"},
        )
        assert create_response.status_code == 201

        short_code = create_response.json()["short_code"]

        stmt = select(LinkStatsModel).join(LinkModel).where(
            LinkModel.short_code == short_code
        )
        result = await db_session.execute(stmt)
        stats_before = result.scalar_one_or_none()
        assert stats_before is not None
        assert stats_before.last_used_at is None

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}"
        )
        assert redirect_response.status_code == 307

        db_session.expire_all()
        result = await db_session.execute(stmt)
        stats_after = result.scalar_one_or_none()
        assert stats_after is not None
        assert stats_after.last_used_at is not None

        now = datetime.now(timezone.utc)
        time_diff = (now - stats_after.last_used_at).total_seconds()
        assert abs(time_diff) < 60

    @pytest.mark.asyncio
    async def test_redirect_nonexistent_link(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        unknown_code = "nonexistent123"
        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{unknown_code}"
        )
        assert redirect_response.status_code == 404
        data = redirect_response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_redirect_expired_link(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers
    ):
        
        future = datetime.now(timezone.utc) + timedelta(days=7)
        future = future.replace(second=0, microsecond=0)

        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://expired.example.com",
                "expires_at": future.isoformat(),
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        link_id = data["link_id"]

        forced_expired_at = datetime.now(timezone.utc) - timedelta(days=1)

        stmt = select(LinkModel).where(LinkModel.id == link_id)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()
        assert link is not None

        link.expired_at = forced_expired_at
        await db_session.commit()
        db_session.expire_all()

        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()
        assert link is not None
        assert link.expired_at is not None
        assert link.expired_at <= datetime.now(timezone.utc)

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}"
        )
        assert redirect_response.status_code == 404

    @pytest.mark.asyncio
    async def test_redirect_deleted_link(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://deleted.example.com"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        link_id = data["link_id"]

        delete_response = await client.delete(
            f"/links/{short_code}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        stmt = select(LinkModel).where(LinkModel.id == link_id)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()
        assert link is not None
        assert link.is_deleted is True

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}"
        )
        assert redirect_response.status_code == 404