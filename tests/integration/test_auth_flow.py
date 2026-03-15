import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.user import UserModel


class TestAuthFlow:
    

    @pytest.mark.asyncio
    async def test_successful_registration(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        email = "test1@example.com"
        password = "securepassword123"

        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.email == email)
        )
        result = await db_session.execute(stmt)
        count_before = result.scalar()
        assert count_before == 0

        response = await client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        assert response.status_code == 201

        data = response.json()
        assert "user_id" in data
        assert isinstance(data["user_id"], str)

        db_session.expire_all()

        stmt = select(UserModel).where(UserModel.email == email)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == email
        assert user.password_hash != password
        assert len(user.password_hash) > 0

        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.email == email)
        )
        result = await db_session.execute(stmt)
        count_after = result.scalar()
        assert count_after == 1

    @pytest.mark.asyncio
    async def test_duplicate_email_registration(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        
        email = "duplicate@example.com"

        response1 = await client.post(
            "/auth/register",
            json={"email": email, "password": "password"},
        )
        assert response1.status_code == 201

        response2 = await client.post(
            "/auth/register",
            json={"email": email, "password": "differentpassword"},
        )
        assert response2.status_code == 409

        data = response2.json()
        assert "detail" in data
        assert "email" in data["detail"].lower()

        db_session.expire_all()

        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.email == email)
        )
        result = await db_session.execute(stmt)
        count = result.scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_successful_login(self, client: AsyncClient):
        
        email = "login@example.com"
        password = "mypassword"

        reg_response = await client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        assert reg_response.status_code == 201

        login_response = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200

        data = login_response.json()
        assert "access_token" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, db_session: AsyncSession):
        
        email = "wrongpass@example.com"
        password = "correctpassword"

        reg_response = await client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        assert reg_response.status_code == 201

        login_response = await client.post(
            "/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )
        assert login_response.status_code == 401

        data = login_response.json()
        assert "detail" in data
        assert (
            "invalid" in data["detail"].lower()
            or "credentials" in data["detail"].lower()
        )

        
        successful_login = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert successful_login.status_code == 200
        assert "access_token" in successful_login.json()

        
        from sqlalchemy import select, func
        from src.infrastructure.db.models.user import UserModel
        stmt = select(func.count()).select_from(UserModel).where(UserModel.email == email)
        result = await db_session.execute(stmt)
        count = result.scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_login_unknown_email(self, client: AsyncClient, db_session: AsyncSession):
        
        email = "nonexistent@example.com"

        
        from sqlalchemy import select, func
        from src.infrastructure.db.models.user import UserModel
        stmt = select(func.count()).select_from(UserModel).where(UserModel.email == email)
        result = await db_session.execute(stmt)
        count_before = result.scalar()
        assert count_before == 0

        login_response = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "anypassword",
            },
        )
        assert login_response.status_code == 404

        data = login_response.json()
        assert "detail" in data
        assert "user" in data["detail"].lower()

        
        result = await db_session.execute(stmt)
        count_after = result.scalar()
        assert count_after == 0