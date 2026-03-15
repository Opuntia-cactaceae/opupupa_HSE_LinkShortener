import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta


class TestLinks:
#ну тут в лоб тест функционала
    @pytest.mark.asyncio
    async def test_create_anonymous_link(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "full_short_url" in data
        assert data["original_url"].startswith("https://example.com")
        assert "expires_at" in data
        assert "created_at" in data
        assert "link_id" in data
        assert "is_expired" in data
        assert data["owner_user_id"] is None
        assert data["clicks"] == 0

    @pytest.mark.asyncio
    async def test_create_authenticated_link(self, client: AsyncClient, auth_headers):
        payload = {
            "original_url": "https://example.com"
        }
        response = await client.post("/links/shorten", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["owner_user_id"] is not None

    @pytest.mark.asyncio
    async def test_create_with_custom_alias(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "sosusen"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["short_code"] == "sosusen"

    @pytest.mark.asyncio
    async def test_create_duplicate_alias(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "duplicate"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201  
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 409  

    @pytest.mark.asyncio
    async def test_create_invalid_url(self, client: AsyncClient):
        payload = {
            "original_url": "not-a-url"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_link_info_success(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "getinfo"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]
        response = await client.get(f"/links/{short_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == short_code
        assert data["original_url"].startswith("https://example.com")
        assert "created_at" in data
        assert "updated_at" in data
        assert "full_short_url" in data
        assert "is_expired" in data

    @pytest.mark.asyncio
    async def test_get_link_info_not_found(self, client: AsyncClient):
        response = await client.get("/links/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_by_owner(self, client: AsyncClient, auth_headers):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "toupdate"
        }
        response = await client.post("/links/shorten", json=payload, headers=auth_headers)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        update_payload = {
            "original_url": "https://updated.example.com",
            "new_short_code": "updatedalias"
        }
        response = await client.put(f"/links/{short_code}", json=update_payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"].startswith("https://updated.example.com")

        response = await client.get("/links/updatedalias")
        assert response.status_code == 200
        assert response.json()["original_url"].startswith("https://updated.example.com")

        response = await client.get(f"/links/{short_code}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_forbidden(self, client: AsyncClient, auth_headers):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "noperm"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        update_payload = {
            "original_url": "https://updated.example.com"
        }
        response = await client.put(f"/links/{short_code}", json=update_payload, headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_unauthorized(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "anonymous"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        update_payload = {
            "original_url": "https://updated.example.com"
        }
        response = await client.put(f"/links/{short_code}", json=update_payload)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_by_owner(self, client: AsyncClient, auth_headers):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "todelete"
        }
        response = await client.post("/links/shorten", json=payload, headers=auth_headers)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        response = await client.delete(f"/links/{short_code}", headers=auth_headers)
        assert response.status_code == 204

        response = await client.get(f"/links/{short_code}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_forbidden(self, client: AsyncClient, auth_headers):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "deleteforbidden"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        response = await client.delete(f"/links/{short_code}", headers=auth_headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_unauthorized(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "deleteanon"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        response = await client.delete(f"/links/{short_code}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_link_stats_success(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "statslink"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        response = await client.get(f"/links/{short_code}/stats")
        assert response.status_code == 200
        data = response.json()

        assert data["short_code"] == short_code
        assert data["clicks"] == 0
        assert "last_used_at" in data
        assert data["last_used_at"] is None

    @pytest.mark.asyncio
    async def test_stats_clicks_updated_after_redirect(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "clicktest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        response = await client.get(f"/links/{short_code}/stats")
        assert response.json()["clicks"] == 0

        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)
        assert response.status_code in (307, 302)

        response = await client.get(f"/links/{short_code}/stats")
        assert response.json()["clicks"] == 1
        assert response.json()["last_used_at"] is not None

    @pytest.mark.asyncio
    async def test_search_success(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com/testus",
            "custom_alias": "searchalias"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201

        response = await client.get("/links/search", params={"original_url": "https://example.com/testus"})
        print(f"Search response: {response.status_code} {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        found = any(item["short_code"] == "searchalias" for item in data["items"])
        assert found

    @pytest.mark.asyncio
    async def test_search_empty(self, client: AsyncClient):
        response = await client.get("/links/search", params={"original_url": "https://susen.example.com"})
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_search_invalid_query(self, client: AsyncClient):
        response = await client.get("/links/search")
        assert response.status_code == 422

        response = await client.get("/links/search", params={"original_url": "not-a-url"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_expired_links_list(self, client: AsyncClient, auth_headers):
        response = await client.get("/links/expired", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_expired_links_pagination_validation(self, client: AsyncClient, auth_headers):
        response = await client.get("/links/expired", params={"page": 0}, headers=auth_headers)
        assert response.status_code == 422

        response = await client.get("/links/expired", params={"size": 101}, headers=auth_headers)
        assert response.status_code == 422

        response = await client.get("/links/expired", params={"size": 0}, headers=auth_headers)
        assert response.status_code == 422

        response = await client.get("/links/expired", params={"page": 1, "size": 10}, headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_extra_fields_rejected(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "extrafield",
            "extra": "field"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_short_code_rejected(self, client: AsyncClient):
        response = await client.get("/links/ab")
        assert response.status_code == 422

        response = await client.get("/links/invalid@code")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_short_code_stats_rejected(self, client: AsyncClient):
        response = await client.get("/links/ab/stats")
        assert response.status_code == 422

        response = await client.get("/links/invalid@code/stats")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_short_code_update_delete_rejected(self, client: AsyncClient):
        response = await client.put("/links/ab", json={"original_url": "https://example.com"})
        assert response.status_code == 422
        response = await client.delete("/links/ab")
        assert response.status_code == 422

        response = await client.put("/links/invalid@code", json={"original_url": "https://example.com"})
        assert response.status_code == 422
        response = await client.delete("/links/invalid@code")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_pagination_rejected(self, client: AsyncClient):
        response = await client.get("/links/search", params={"original_url": "https://example.com", "page": 0})
        assert response.status_code == 422

        response = await client.get("/links/search", params={"original_url": "https://example.com", "size": 101})
        assert response.status_code == 422

        response = await client.get("/links/search", params={"original_url": "https://example.com", "size": 0})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_expires_at_rejected(self, client: AsyncClient):
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        past = past.replace(second=0, microsecond=0)
        payload = {
            "original_url": "https://example.com",
            "expires_at": past.isoformat()
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_bad_expires_at_rejected(self, client: AsyncClient, auth_headers):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "updateexpires"
        }
        response = await client.post("/links/shorten", json=payload, headers=auth_headers)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        past = past.replace(second=0, microsecond=0)
        update_payload = {
            "expires_at": past.isoformat()
        }
        response = await client.put(
            f"/links/{short_code}",
            json=update_payload,
            headers=auth_headers,
        )
        assert response.status_code == 422

        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        future = future.replace(second=0, microsecond=0)
        update_payload = {
            "expires_at": future.isoformat()
        }
        response = await client.put(
            f"/links/{short_code}",
            json=update_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_extra_fields_rejected(self, client: AsyncClient):
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "extraupdate"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]
        update_payload = {
            "original_url": "https://updated.example.com",
            "extra": "field"
        }

        response = await client.put(f"/links/{short_code}", json=update_payload)
        assert response.status_code == 422