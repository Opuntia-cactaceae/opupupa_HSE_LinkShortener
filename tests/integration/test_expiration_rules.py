import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link import LinkModel
from src.infrastructure.db.models.link_stats import LinkStatsModel
from src.infrastructure.settings import settings


class TestExpirationRules:
    

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        
        unique_email = f"expireuser_{uuid.uuid4().hex[:8]}@example.com"

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

    async def _create_link_with_future_expiration(
        self,
        client: AsyncClient,
        original_url: str,
        headers: dict | None = None,
    ) -> dict:
        
        future = datetime.now(timezone.utc) + timedelta(days=7)
        future = future.replace(second=0, microsecond=0)

        response = await client.post(
            "/links/shorten",
            json={
                "original_url": original_url,
                "expires_at": future.isoformat(),
            },
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()

    async def _mark_link_expired_in_db(
        self,
        db_session: AsyncSession,
        link_id: str,
        expired_at: datetime | None = None,
    ) -> LinkModel:
        
        if expired_at is None:
            expired_at = datetime.now(timezone.utc) - timedelta(days=1)

        link_uuid = uuid.UUID(link_id)
        stmt = select(LinkModel).where(LinkModel.id == link_uuid)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()
        assert link is not None

        link.expired_at = expired_at
        await db_session.commit()
        db_session.expire_all()

        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()
        assert link is not None
        assert link.expired_at is not None
        return link

    @pytest.mark.asyncio
    async def test_expired_link_hidden_from_redirect(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers,
    ):
        
        data = await self._create_link_with_future_expiration(
            client,
            "https://expired-redirect.example.com",
            headers=auth_headers,
        )
        short_code = data["short_code"]
        link_id = data["link_id"]

        link = await self._mark_link_expired_in_db(db_session, link_id)
        assert link.expired_at <= datetime.now(timezone.utc)

        stats_stmt = select(LinkStatsModel).where(
            LinkStatsModel.link_id == uuid.UUID(link_id)
        )
        result = await db_session.execute(stats_stmt)
        stats_before = result.scalar_one_or_none()
        assert stats_before is not None
        assert stats_before.clicks == 0

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect_response.status_code == 404

        db_session.expire_all()
        result = await db_session.execute(stats_stmt)
        stats_after = result.scalar_one_or_none()
        assert stats_after is not None
        assert stats_after.clicks == 0

    @pytest.mark.asyncio
    async def test_expired_link_visible_in_expired_endpoint(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers,
    ):
        
        data = await self._create_link_with_future_expiration(
            client,
            "https://expired-list.example.com",
            headers=auth_headers,
        )
        short_code = data["short_code"]
        link_id = data["link_id"]

        forced_expired_at = datetime.now(timezone.utc) - timedelta(days=1)
        link = await self._mark_link_expired_in_db(
            db_session,
            link_id,
            expired_at=forced_expired_at,
        )
        assert link.expired_at is not None

        expired_response = await client.get(
            "/links/expired",
            headers=auth_headers,
        )
        assert expired_response.status_code == 200

        expired_items = expired_response.json()
        assert isinstance(expired_items, list)

        found_item = None
        for item in expired_items:
            if item["short_code"] == short_code:
                found_item = item
                break

        assert found_item is not None, f"Expired link {short_code} not found in /links/expired"
        assert found_item["original_url"] == data["original_url"]
        assert found_item["expired_at"] is not None

        item_expired = datetime.fromisoformat(
            found_item["expired_at"].replace("Z", "+00:00")
        )
        assert abs((item_expired - forced_expired_at).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_anonymous_expired_links_are_returned(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        data = await self._create_link_with_future_expiration(
            client,
            "https://anon-expired.example.com",
            headers=None,
        )
        short_code = data["short_code"]
        link_id = data["link_id"]

        stmt = select(LinkModel).where(LinkModel.id == uuid.UUID(link_id))
        result = await db_session.execute(stmt)
        link_before = result.scalar_one_or_none()
        assert link_before is not None
        assert link_before.owner_user_id is None

        forced_expired_at = datetime.now(timezone.utc) - timedelta(days=1)
        link_after = await self._mark_link_expired_in_db(
            db_session,
            link_id,
            expired_at=forced_expired_at,
        )
        assert link_after.owner_user_id is None
        assert link_after.expired_at is not None

        expired_response = await client.get("/links/expired")
        assert expired_response.status_code == 200

        expired_items = expired_response.json()
        assert isinstance(expired_items, list)

        found_item = None
        for item in expired_items:
            if item["short_code"] == short_code:
                found_item = item
                break

        assert found_item is not None, f"Anonymous expired link {short_code} not found in /links/expired"
        assert found_item["owner_user_id"] is None
        assert found_item["original_url"] == data["original_url"]
        assert found_item["expired_at"] is not None

        item_expired = datetime.fromisoformat(
            found_item["expired_at"].replace("Z", "+00:00")
        )
        assert abs((item_expired - forced_expired_at).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_update_expiration(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers,
    ):
        
        far_future = datetime.now(timezone.utc) + timedelta(days=30)
        far_future = far_future.replace(second=0, microsecond=0)

        create_response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://update-expire.example.com",
                "expires_at": far_future.isoformat(),
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        link_id = data["link_id"]

        nearer_future = datetime.now(timezone.utc) + timedelta(days=7)
        nearer_future = nearer_future.replace(second=0, microsecond=0)

        update_response = await client.put(
            f"/links/{short_code}",
            json={"expires_at": nearer_future.isoformat()},
            headers=auth_headers,
        )
        assert update_response.status_code == 200

        update_data = update_response.json()
        assert update_data["expires_at"] is not None

        resp_expires = datetime.fromisoformat(
            update_data["expires_at"].replace("Z", "+00:00")
        )
        assert abs((resp_expires - nearer_future).total_seconds()) < 1

        db_session.expire_all()
        stmt = select(LinkModel).where(LinkModel.id == uuid.UUID(link_id))
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.expires_at is not None
        assert link.expires_at.replace(tzinfo=timezone.utc) == nearer_future