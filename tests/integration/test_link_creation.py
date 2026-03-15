import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link import LinkModel
from src.infrastructure.db.models.link_stats import LinkStatsModel
from src.infrastructure.db.models.user import UserModel


class TestLinkCreation:
    """
    Тут уже интеграционные тесты создания коротких ссылок:
    - создание анонимной и авторизованной ссылки;
    - создание ссылки с кодом;
    - обработка дубликатов кода;
    - работа протухания для анонимных и авторизованных пользователей;
    - запрет назначения проекта для анонимных пользователей;
    - валидация некорректного URL.
    (еще сохранение LinkModel и LinkStatsModel в бд)
    """

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        
        unique_email = f"linkuser_{uuid.uuid4().hex[:8]}@example.com"

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
    async def project_id(self, client: AsyncClient, auth_headers) -> uuid.UUID:
        
        response = await client.post(
            "/projects/",
            json={"name": "Test Project"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        return uuid.UUID(response.json()["id"])

    @pytest.mark.asyncio
    async def test_create_anonymous_link(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        before_request = datetime.now(timezone.utc)
        before_expected = (before_request + timedelta(days=10)).replace(second=0, microsecond=0)

        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com"},
        )
        assert response.status_code == 201

        after_request = datetime.now(timezone.utc)
        after_expected = (after_request + timedelta(days=10)).replace(second=0, microsecond=0)

        data = response.json()

        assert "short_code" in data
        assert "full_short_url" in data
        assert data["original_url"] == "https://example.com/"
        assert data["owner_user_id"] is None
        assert data["clicks"] == 0
        assert data["expires_at"] is not None

        response_expires_at = datetime.fromisoformat(
            data["expires_at"].replace("Z", "+00:00")
        )

        assert before_expected <= response_expires_at <= after_expected

        stmt = select(LinkModel).where(LinkModel.short_code == data["short_code"])
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.original_url == "https://example.com/"
        assert link.owner_user_id is None
        assert link.is_deleted is False
        assert link.expires_at is not None

        db_expires_at = (
            link.expires_at.replace(tzinfo=timezone.utc)
            if link.expires_at.tzinfo is None
            else link.expires_at.astimezone(timezone.utc)
        )
        assert before_expected <= db_expires_at <= after_expected

        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id == link.id)
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()

        assert stats is not None
        assert stats.clicks == 0
        assert stats.last_used_at is None

    @pytest.mark.asyncio
    async def test_create_authenticated_link(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers,
    ):
        
        response = await client.post(
            "/links/shorten",
            json={"original_url": "https://example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert data["owner_user_id"] is not None
        assert data["original_url"] == "https://example.com/"
        assert data["expires_at"] is None

        stmt = select(LinkModel).where(LinkModel.short_code == data["short_code"])
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.owner_user_id is not None
        assert link.original_url == "https://example.com/"
        assert link.expires_at is None

        stmt = select(UserModel).where(UserModel.id == link.owner_user_id)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()
        assert user is not None

        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id == link.id)
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()
        assert stats is not None
        assert stats.clicks == 0

    @pytest.mark.asyncio
    async def test_create_with_custom_alias(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        alias = "myalias123"

        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com",
                "custom_alias": alias,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["short_code"] == alias
        assert data["original_url"] == "https://example.com/"
        assert data["expires_at"] is not None  

        stmt = select(LinkModel).where(LinkModel.short_code == alias)
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.short_code == alias
        assert link.original_url == "https://example.com/"
        assert link.owner_user_id is None
        assert link.expires_at is not None

        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id == link.id)
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()

        assert stats is not None
        assert stats.clicks == 0

    @pytest.mark.asyncio
    async def test_duplicate_alias_returns_conflict(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        alias = "duplicate123"
        payload = {
            "original_url": "https://example.com",
            "custom_alias": alias,
        }

        response1 = await client.post("/links/shorten", json=payload)
        assert response1.status_code == 201

        data1 = response1.json()
        link_id = uuid.UUID(data1["link_id"])

        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id == link_id)
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()

        assert stats is not None
        assert stats.clicks == 0

        response2 = await client.post("/links/shorten", json=payload)
        assert response2.status_code == 409

        data2 = response2.json()
        assert "detail" in data2
        assert (
            "already exists" in data2["detail"].lower()
            or "short code" in data2["detail"].lower()
        )

        stmt = (
            select(func.count())
            .select_from(LinkModel)
            .where(LinkModel.short_code == alias)
        )
        result = await db_session.execute(stmt)
        count = result.scalar()

        assert count == 1

    @pytest.mark.asyncio
    async def test_create_authenticated_link_with_expiration(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers,
    ):
        
        future = datetime.now(timezone.utc) + timedelta(days=7)
        future = future.replace(second=0, microsecond=0)

        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com",
                "expires_at": future.isoformat(),
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        data = response.json()
        assert data["expires_at"] is not None

        response_expires_at = datetime.fromisoformat(
            data["expires_at"].replace("Z", "+00:00")
        )
        assert abs((response_expires_at - future).total_seconds()) < 1

        stmt = select(LinkModel).where(LinkModel.short_code == data["short_code"])
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        assert link.expires_at is not None

        db_expires_at = (
            link.expires_at.replace(tzinfo=timezone.utc)
            if link.expires_at.tzinfo is None
            else link.expires_at.astimezone(timezone.utc)
        )
        assert abs((db_expires_at - future).total_seconds()) < 1

        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id == link.id)
        result = await db_session.execute(stmt)
        stats = result.scalar_one_or_none()

        assert stats is not None
        assert stats.clicks == 0

    @pytest.mark.asyncio
    async def test_anonymous_ignores_client_expires_at_and_gets_default_ttl(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        requested_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        requested_expires_at = requested_expires_at.replace(second=0, microsecond=0)

        before_request = datetime.now(timezone.utc)
        before_expected = (before_request + timedelta(days=10)).replace(second=0, microsecond=0)

        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com",
                "expires_at": requested_expires_at.isoformat(),
            },
        )
        assert response.status_code == 201

        after_request = datetime.now(timezone.utc)
        after_expected = (after_request + timedelta(days=10)).replace(second=0, microsecond=0)

        data = response.json()

        actual_expires_at = datetime.fromisoformat(
            data["expires_at"].replace("Z", "+00:00")
        )

        assert before_expected <= actual_expires_at <= after_expected
        assert abs((actual_expires_at - requested_expires_at).total_seconds()) > 60

        stmt = select(LinkModel).where(LinkModel.short_code == data["short_code"])
        result = await db_session.execute(stmt)
        link = result.scalar_one_or_none()

        assert link is not None
        db_expires_at = (
            link.expires_at.replace(tzinfo=timezone.utc)
            if link.expires_at.tzinfo is None
            else link.expires_at.astimezone(timezone.utc)
        )
        assert before_expected <= db_expires_at <= after_expected

    @pytest.mark.asyncio
    async def test_anonymous_cannot_assign_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project_id,
    ):
        
        stmt = (
            select(func.count())
            .select_from(LinkModel)
            .where(LinkModel.project_id == project_id)
        )
        result = await db_session.execute(stmt)
        count_before = result.scalar()
        assert count_before == 0

        response = await client.post(
            "/links/shorten",
            json={
                "original_url": "https://example.com",
                "project_id": str(project_id),
            },
        )

        assert response.status_code in (400, 403, 422)
        data = response.json()
        assert "detail" in data

        result = await db_session.execute(stmt)
        count_after = result.scalar()
        assert count_after == 0

    @pytest.mark.asyncio
    async def test_invalid_url_returns_validation_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        stmt = select(func.count()).select_from(LinkModel)
        result = await db_session.execute(stmt)
        count_before = result.scalar()
        assert count_before == 0

        response = await client.post(
            "/links/shorten",
            json={"original_url": "not-a-valid-url"},
        )
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

        result = await db_session.execute(stmt)
        count_after = result.scalar()
        assert count_after == 0