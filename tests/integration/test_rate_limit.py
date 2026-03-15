import uuid

import pytest
from httpx import AsyncClient

from src.infrastructure.settings import settings


class TestRateLimit:
    """
    Лимиты:
    - превышение лимита запросов для эндпоинта входа (/auth/login);
    - превышение лимита для эндпоинта редиректа короткой ссылки;
    - корректный возврат HTTP 429 и заголовка;
    - создание и обновление ключей лимитов в редиске;
    - сброс лимита после окончания окна.
    """

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        
        unique_email = f"ratelimituser_{uuid.uuid4().hex[:8]}@example.com"

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
    async def test_login_rate_limit_exceeded(
        self,
        client: AsyncClient,
        redis_client,
    ):
        
        limit = 5

        last_response = None
        for i in range(limit + 1):
            response = await client.post(
                "/auth/login",
                json={
                    "email": f"nonexistent{i}@example.com",
                    "password": "wrongpassword",
                },
            )

            last_response = response

            if i < limit:
                assert response.status_code != 429
            else:
                assert response.status_code == 429
                data = response.json()
                assert "detail" in data
                assert data["detail"] == "Rate limit exceeded"
                assert response.headers["Retry-After"] == "60"

        assert last_response is not None

        keys = await redis_client.client.keys("rate_limit:*:POST:/auth/login")
        assert len(keys) > 0

        key = keys[0]
        count = await redis_client.client.zcard(key)
        assert count >= limit

        ttl = await redis_client.client.ttl(key)
        assert 0 < ttl <= 60

    @pytest.mark.asyncio
    async def test_redirect_rate_limit(
        self,
        client: AsyncClient,
        redis_client,
        auth_headers,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://ratelimit.example.com"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        short_code = create_response.json()["short_code"]
        redirect_path = f"/{settings.SHORT_LINK_PREFIX}/{short_code}"

        limit = 100
        successful_responses = 0

        for i in range(limit + 1):
            response = await client.get(
                redirect_path,
                follow_redirects=False,
            )

            if i < limit:
                assert response.status_code == 307
                successful_responses += 1
            else:
                assert response.status_code == 429
                data = response.json()
                assert "detail" in data
                assert data["detail"] == "Rate limit exceeded"
                assert response.headers["Retry-After"] == "60"

        assert successful_responses == limit

        keys = await redis_client.client.keys("rate_limit:*:GET:/opupupa/")
        assert len(keys) > 0

        key = keys[0]
        count = await redis_client.client.zcard(key)
        assert count >= limit

        ttl = await redis_client.client.ttl(key)
        assert 0 < ttl <= 60

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(
        self,
        client: AsyncClient,
        redis_client,
    ):
        
        limit = 5

        for i in range(limit + 1):
            response = await client.post(
                "/auth/login",
                json={
                    "email": f"reset{i}@example.com",
                    "password": "wrongpassword",
                },
            )

            if i < limit:
                assert response.status_code != 429
            else:
                assert response.status_code == 429

        keys = await redis_client.client.keys("rate_limit:*:POST:/auth/login")
        assert len(keys) > 0
        key = keys[0]

        ttl = await redis_client.client.ttl(key)
        assert 0 < ttl <= 60

        await redis_client.client.delete(key)

        response = await client.post(
            "/auth/login",
            json={
                "email": "afterreset@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code != 429

        keys = await redis_client.client.keys("rate_limit:*:POST:/auth/login")
        assert len(keys) > 0

        new_key = keys[0]
        count = await redis_client.client.zcard(new_key)
        assert count == 1