import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link import LinkModel
from src.infrastructure.db.models.link_stats import LinkStatsModel
from src.infrastructure.settings import settings


class TestLinkStats:
    

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        
        unique_email = f"statsuser_{uuid.uuid4().hex[:8]}@example.com"
        register_payload = {
            "email": unique_email,
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201

        login_payload = {
            "email": unique_email,
            "password": "password"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_stats_for_new_link(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        
        payload = {"original_url": "https://example.com"}
        create_response = await client.post("/links/shorten", json=payload)
        assert create_response.status_code == 201
        data = create_response.json()
        short_code = data["short_code"]

        
        stats_response = await client.get(f"/links/{short_code}/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["short_code"] == short_code
        assert stats_data["clicks"] == 0
        assert stats_data["last_used_at"] is None

        
        stmt = select(LinkStatsModel).join(LinkModel).where(
            LinkModel.short_code == short_code
        )
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()
        assert stats is not None
        assert stats.clicks == 0
        assert stats.last_used_at is None

    @pytest.mark.asyncio
    async def test_stats_after_redirects(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        
        payload = {"original_url": "https://example.org"}
        create_response = await client.post("/links/shorten", json=payload)
        assert create_response.status_code == 201
        data = create_response.json()
        short_code = data["short_code"]

        
        redirect_count = 3
        for i in range(redirect_count):
            redirect_response = await client.get(
                f"/{settings.SHORT_LINK_PREFIX}/{short_code}"
            )
            assert redirect_response.status_code == 307

        
        stats_response = await client.get(f"/links/{short_code}/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["short_code"] == short_code
        assert stats_data["clicks"] == redirect_count
        assert stats_data["last_used_at"] is not None

        
        stmt = select(LinkStatsModel).join(LinkModel).where(
            LinkModel.short_code == short_code
        )
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()
        assert stats is not None
        assert stats.clicks == redirect_count
        assert stats.last_used_at is not None
        
        now = datetime.now(timezone.utc)
        time_diff = (now - stats.last_used_at).total_seconds()
        assert abs(time_diff) < 60

    @pytest.mark.asyncio
    async def test_stats_for_nonexistent_link(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        unknown_code = "nonexistent456"
        stats_response = await client.get(f"/links/{unknown_code}/stats")
        assert stats_response.status_code == 404
        data = stats_response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_stats_for_deleted_link(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers
    ):
        
        
        payload = {"original_url": "https://deleted.example.com"}
        create_response = await client.post(
            "/links/shorten", json=payload, headers=auth_headers
        )
        assert create_response.status_code == 201
        data = create_response.json()
        short_code = data["short_code"]
        link_id = data["link_id"]

        
        delete_response = await client.delete(
            f"/links/{short_code}", headers=auth_headers
        )
        assert delete_response.status_code == 204

        
        stmt = select(LinkModel).where(LinkModel.id == link_id)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()
        assert link is not None
        assert link.is_deleted is True

        
        stats_response = await client.get(f"/links/{short_code}/stats")
        assert stats_response.status_code == 404