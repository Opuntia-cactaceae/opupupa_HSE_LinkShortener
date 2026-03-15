import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link import LinkModel
from src.infrastructure.settings import settings


class TestLinkUpdateDelete:
    

    @pytest.fixture
    async def auth_headers_a(self, client: AsyncClient) -> dict:
        
        unique_email = f"user_a_{uuid.uuid4().hex[:8]}@example.com"

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

    @pytest.fixture
    async def auth_headers_b(self, client: AsyncClient) -> dict:
        
        unique_email = f"user_b_{uuid.uuid4().hex[:8]}@example.com"

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
    async def test_owner_updates_link(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://original.example.com"},
            headers=auth_headers_a,
        )
        assert create_response.status_code == 201

        short_code = create_response.json()["short_code"]

        future = datetime.now(timezone.utc) + timedelta(days=14)
        future = future.replace(second=0, microsecond=0)

        update_response = await client.put(
            f"/links/{short_code}",
            json={
                "original_url": "https://updated.example.com",
                "expires_at": future.isoformat(),
            },
            headers=auth_headers_a,
        )
        assert update_response.status_code == 200

        update_data = update_response.json()
        assert update_data["original_url"] == "https://updated.example.com/"
        assert update_data["expires_at"] is not None

        resp_expires = datetime.fromisoformat(
            update_data["expires_at"].replace("Z", "+00:00")
        )
        assert abs((resp_expires - future).total_seconds()) < 1

        db_session.expire_all()
        stmt = select(LinkModel).where(LinkModel.short_code == short_code)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.original_url == "https://updated.example.com/"
        assert link.expires_at is not None
        assert link.expires_at.replace(tzinfo=timezone.utc) == future

    @pytest.mark.asyncio
    async def test_anonymous_updates_anonymous_link(
        self,
        client: AsyncClient,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://anon.example.com"},
        )
        assert create_response.status_code == 201

        short_code = create_response.json()["short_code"]

        update_response = await client.put(
            f"/links/{short_code}",
            json={"original_url": "https://anon-updated.example.com"},
        )
        assert update_response.status_code == 403

        
        info_response = await client.get(f"/links/{short_code}")
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert info_data["original_url"] == "https://anon.example.com/"

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect_response.status_code == 307
        assert redirect_response.headers["Location"] == "https://anon.example.com/"

    @pytest.mark.asyncio
    async def test_non_owner_tries_to_update_link(
        self,
        client: AsyncClient,
        auth_headers_a,
        auth_headers_b,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://user-a.example.com"},
            headers=auth_headers_a,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]

        update_response = await client.put(
            f"/links/{short_code}",
            json={"original_url": "https://user-b-attempt.example.com"},
            headers=auth_headers_b,
        )
        assert update_response.status_code == 403

        info_response = await client.get(f"/links/{short_code}")
        assert info_response.status_code == 200

        info_data = info_response.json()
        assert info_data["original_url"] == "https://user-a.example.com/"

    @pytest.mark.asyncio
    async def test_owner_deletes_link(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://delete.example.com"},
            headers=auth_headers_a,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        link_id = data["link_id"]

        delete_response = await client.delete(
            f"/links/{short_code}",
            headers=auth_headers_a,
        )
        assert delete_response.status_code == 204

        db_session.expire_all()
        stmt = select(LinkModel).where(LinkModel.id == link_id)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.is_deleted is True

    @pytest.mark.asyncio
    async def test_anonymous_deletes_anonymous_link(
        self,
        client: AsyncClient,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://anon-delete.example.com"},
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]

        delete_response = await client.delete(f"/links/{short_code}")
        assert delete_response.status_code == 403

        
        info_response = await client.get(f"/links/{short_code}")
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert info_data["original_url"] == "https://anon-delete.example.com/"

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect_response.status_code == 307
        assert redirect_response.headers["Location"] == "https://anon-delete.example.com/"

    @pytest.mark.asyncio
    async def test_delete_invalidates_redirect(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        create_response = await client.post(
            "/links/shorten",
            json={"original_url": "https://redirect-invalidate.example.com"},
            headers=auth_headers_a,
        )
        assert create_response.status_code == 201

        data = create_response.json()
        short_code = data["short_code"]
        link_id = data["link_id"]

        delete_response = await client.delete(
            f"/links/{short_code}",
            headers=auth_headers_a,
        )
        assert delete_response.status_code == 204

        db_session.expire_all()
        stmt = select(LinkModel).where(LinkModel.id == link_id)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.is_deleted is True

        redirect_response = await client.get(
            f"/{settings.SHORT_LINK_PREFIX}/{short_code}",
            follow_redirects=False,
        )
        assert redirect_response.status_code == 404