import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestAuth:
    """Functional tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """POST /auth/register with valid data should create user."""
        payload = {
            "email": "test@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert isinstance(data["user_id"], str)
        # Ensure email is not leaked
        assert "email" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        """POST /auth/register with duplicate email should fail."""
        payload = {
            "email": "duplicate@example.com",
            "password": "password"
        }
        # First registration succeeds
        response1 = await client.post("/auth/register", json=payload)
        assert response1.status_code == 201
        # Second registration fails
        response2 = await client.post("/auth/register", json=payload)
        assert response2.status_code == 409
        data = response2.json()
        assert "detail" in data
        assert "email" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_input(self, client: AsyncClient):
        """POST /auth/register with invalid input should return 422."""
        # Short password
        payload = {
            "email": "test@example.com",
            "password": "short"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422
        # Invalid email
        payload = {
            "email": "not-an-email",
            "password": "password"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422
        # Missing email
        payload = {
            "password": "password"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422
        # Extra fields should be rejected (extra="forbid")
        payload = {
            "email": "test@example.com",
            "password": "password",
            "extra": "field"
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """POST /auth/login with valid credentials should return token."""
        # First register a user
        register_payload = {
            "email": "login@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201
        # Then login
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
        """POST /auth/login with wrong password should fail."""
        # Register user
        register_payload = {
            "email": "invalidpass@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201
        # Attempt login with wrong password
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
        """POST /auth/login with unknown email should fail."""
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
        """Extra fields in login request should be rejected."""
        # First register a user
        register_payload = {
            "email": "extra@example.com",
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201
        # Attempt login with extra field
        login_payload = {
            "email": "extra@example.com",
            "password": "password",
            "extra": "field"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 422