import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link_stats import LinkStatsModel
from src.infrastructure.settings import settings


class TestCacheInvalidation:
    

    def _make_cache_key(self, short_code: str) -> str:
        return f"link:code:{short_code}"

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        unique_email = f"cacheuser_{uuid.uuid4().hex[:8]}@example.com"

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
    async def test_create_link_sets_cache(
        self,
        client: AsyncClient,
        redis_client,
    ):
        
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://cache1.example.com"},
        )
        assert response.status_code == 201

        data = response.json()
        short_code = data["short_code"]

        cache_key = self._make_cache_key(short_code)
        cached = await redis_client.client.get(cache_key)
        assert cached is not None

        cache_data = json.loads(cached)
        assert cache_data["original_url"] == "https://cache1.example.com/"
        assert "link_id" in cache_data
        assert "expires_at" in cache_data

    @pytest.mark.asyncio
    async def test_redirect_with_existing_cache_still_increments_stats(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        redis_client,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://cache2.example.com"},
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        original_url = data["original_url"]
        link_id = data["link_id"]

        cache_key = self._make_cache_key(short_code)
        cached_before = await redis_client.client.get(cache_key)
        assert cached_before is not None

        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id == link_id)

        redirect1_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect1_response.status_code == 307
        assert redirect1_response.headers["Location"] == original_url

        db_session.expire_all()
        result = await db_session.execute(stmt)
        stats_after_first = result.scalar_one_or_none()
        assert stats_after_first is not None
        assert stats_after_first.clicks == 1

        redirect2_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect2_response.status_code == 307
        assert redirect2_response.headers["Location"] == original_url

        db_session.expire_all()
        result = await db_session.execute(stmt)
        stats_after_second = result.scalar_one_or_none()
        assert stats_after_second is not None
        assert stats_after_second.clicks == 2

        cached_after = await redis_client.client.get(cache_key)
        assert cached_after is not None

    @pytest.mark.asyncio
    async def test_update_invalidates_cache(
        self,
        client: AsyncClient,
        redis_client,
        auth_headers,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://cache-update1.example.com"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        cache_key = self._make_cache_key(short_code)

        cached_before = await redis_client.client.get(cache_key)
        assert cached_before is not None

        update_response = await client.put(
            f"/links/{short_code}",
            json={"original_url": "https://cache-update2.example.com"},
            headers=auth_headers,
        )
        assert update_response.status_code == 200

        update_data = update_response.json()
        assert update_data["original_url"] == "https://cache-update2.example.com/"

        cached_after_update = await redis_client.client.get(cache_key)
        assert cached_after_update is None

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect_response.status_code == 307
        assert "cache-update2.example.com" in redirect_response.headers["Location"]

        cached_after_redirect = await redis_client.client.get(cache_key)
        assert cached_after_redirect is not None

        cache_data = json.loads(cached_after_redirect)
        assert cache_data["original_url"] == "https://cache-update2.example.com/"

    @pytest.mark.asyncio
    async def test_delete_invalidates_cache(
        self,
        client: AsyncClient,
        redis_client,
        auth_headers,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://cache-delete.example.com"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        cache_key = self._make_cache_key(short_code)

        cached_before = await redis_client.client.get(cache_key)
        assert cached_before is not None

        delete_response = await client.delete(
            f"/links/{short_code}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        cached_after_delete = await redis_client.client.get(cache_key)
        assert cached_after_delete is None

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect_response.status_code == 404