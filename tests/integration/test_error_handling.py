import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link import LinkModel


class TestErrorHandling:
    

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        
        unique_email = f"erroruser_{uuid.uuid4().hex[:8]}@example.com"

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
    async def test_invalid_url(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        redis_client,
    ):
        
        stmt = select(func.count()).select_from(LinkModel)
        result = await db_session.execute(stmt)
        count_before = result.scalar()

        response = await client.post(
            "/links/shorten",
            json={"original_url": "not-a-valid-url"},
        )

        assert response.status_code in (400, 422)
        data = response.json()
        assert "detail" in data

        result = await db_session.execute(stmt)
        count_after = result.scalar()
        assert count_after == count_before

        
        keys = await redis_client.client.keys("link:code:*")
        assert isinstance(keys, list)
        
        
        
        

    @pytest.mark.asyncio
    async def test_invalid_short_code(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        redis_client,
    ):
        
        invalid_codes = [
            "ab",
            "a" * 33,
            "invalid@code",
            "invalid code",
            "invalid#code",
        ]

        for short_code in invalid_codes:
            response = await client.get(f"/links/{short_code}")
            assert response.status_code in (400, 404, 422)
            data = response.json()
            assert "detail" in data

            response = await client.get(f"/links/{short_code}/stats")
            assert response.status_code in (400, 404, 422)
            data = response.json()
            assert "detail" in data

        valid_format_code = "validbutnonexistent123"
        response = await client.get(f"/links/{valid_format_code}")
        assert response.status_code in (404, 400, 422)

    @pytest.mark.asyncio
    async def test_invalid_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://pagination.example.com"},
        )
        assert create_response.status_code == 201
        normalized_url = create_response.json()["original_url"]
        short_code = create_response.json()["short_code"]

        invalid_params = [
            {"page": 0, "size": 20},
            {"page": 1, "size": 0},
            {"page": -1, "size": 20},
            {"page": 1, "size": -5},
            {"page": 1, "size": 101},
        ]

        for params in invalid_params:
            response = await client.get(
                "/links/search",
                params={"original_url": normalized_url, **params},
            )
            assert response.status_code in (400, 422)
            data = response.json()
            assert "detail" in data

            
            link_info = await client.get(f"/links/{short_code}")
            assert link_info.status_code == 200
            assert link_info.json()["original_url"] == normalized_url

        response = await client.get("/links/expired", params={"page": 0, "size": 20})
        assert response.status_code in (200, 401, 422)

        for params in invalid_params[:2]:
            response = await client.get(
                "/links/expired",
                params=params,
                headers=auth_headers,
            )
            assert response.status_code in (400, 422)
            data = response.json()
            assert "detail" in data

            
            link_info = await client.get(f"/links/{short_code}")
            assert link_info.status_code == 200
            assert link_info.json()["original_url"] == normalized_url

    @pytest.mark.asyncio
    async def test_invalid_jwt(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        redis_client,
    ):
        
        invalid_tokens = [
            "invalidtoken",
            "Bearer invalid",
            f"Bearer {uuid.uuid4()}",
            "",
        ]

        for token in invalid_tokens:
            headers = {"Authorization": token} if token else {}

            response = await client.post(
                "/projects/",
                json={"name": "Test Project"},
                headers=headers,
            )
            assert response.status_code in (401, 403)
            data = response.json()
            assert "detail" in data

            response = await client.get("/projects/", headers=headers)
            assert response.status_code in (401, 403)
            data = response.json()
            assert "detail" in data

        from src.infrastructure.db.models.project import ProjectModel

        stmt = select(func.count()).select_from(ProjectModel)
        result = await db_session.execute(stmt)
        project_count = result.scalar()
        
        assert project_count == 0