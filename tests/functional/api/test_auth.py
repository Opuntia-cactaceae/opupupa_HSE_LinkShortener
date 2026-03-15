import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestAuth:

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        payload = {
            "email": "test@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert isinstance(data["user_id"], str)
        assert "email" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "duplicate@example.com",
            "password": "password"
        }
        response1 = await client.post("/auth/register", json=payload)
        assert response1.status_code == 201

        response2 = await client.post("/auth/register", json=payload)
        assert response2.status_code == 409
        data = response2.json()

        assert "detail" in data
        assert "email" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_input(self, client: AsyncClient):

        payload = {
            "email": "test@example.com",
            "password": "short"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422

        payload = {
            "email": "not-an-email",
            "password": "password"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422

        payload = {
            "password": "password"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422

        payload = {
            "email": "test@example.com",
            "password": "password",
            "extra": "field"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        

        register_payload = {
            "email": "login@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201

        login_payload = {
            "email": "login@example.com",
            "password": "password"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient):
        register_payload = {
            "email": "invalidpass@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201

        login_payload = {
            "email": "invalidpass@example.com",
            "password": "wrongpassword"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client: AsyncClient):
        login_payload = {
            "email": "nonexistent@example.com",
            "password": "password"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_login_extra_fields_rejected(self, client: AsyncClient):
        register_payload = {
            "email": "extra@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201

        login_payload = {
            "email": "extra@example.com",
            "password": "password",
            "extra": "field"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 422