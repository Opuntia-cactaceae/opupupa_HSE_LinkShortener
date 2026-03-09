import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta


class TestRedirect:
    @pytest.mark.asyncio
    async def test_redirect_success(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "redirecttest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)
        assert response.status_code == 307
        assert "location" in response.headers
        assert response.headers["location"] in ("https://example.com", "https://example.com/")

    @pytest.mark.asyncio
    async def test_redirect_unknown(self, client: AsyncClient):
        response = await client.get("/opupupa/nonexistent", follow_redirects=False)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_redirect_invalid_short_code(self, client: AsyncClient):
        response = await client.get("/opupupa/invalid@code", follow_redirects=False)
        assert response.status_code == 422
        response = await client.get("/opupupa/ab", follow_redirects=False)
        assert response.status_code == 422