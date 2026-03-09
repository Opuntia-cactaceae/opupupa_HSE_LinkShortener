import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import UUID


class TestProjects:

    @pytest.fixture
    async def auth_headers_user1(self, client: AsyncClient):
        import uuid
        unique_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
        register_payload = {
            "email": unique_email,
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201
        login_payload = {
            "email": unique_email,
            "password": "password"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def auth_headers_user2(self, client: AsyncClient):
        import uuid
        unique_email = f"user2_{uuid.uuid4().hex[:8]}@example.com"
        register_payload = {
            "email": unique_email,
            "password": "password"
        }
        response = await client.post("/auth/register", json=register_payload)
        assert response.status_code == 201
        login_payload = {
            "email": unique_email,
            "password": "password"
        }
        response = await client.post("/auth/login", json=login_payload)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def project_id(self, client: AsyncClient, auth_headers_user1):
        payload = {
            "name": "Test Project"
        }
        response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
        assert response.status_code == 201
        data = response.json()
        return data["id"]

    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers_user1):
        payload = {
            "name": "My Project"
        }
        response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "My Project"
        assert "owner_user_id" in data
        assert "created_at" in data
        assert "updated_at" in data

        try:
            UUID(data["owner_user_id"])
        except ValueError:
            pytest.fail("owner_user_id is not a valid UUID")

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers_user1):
        for i in range(2):
            payload = {"name": f"Project {i}"}
            response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
            assert response.status_code == 201
        response = await client.get("/projects/", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        for project in data:
            assert "id" in project
            assert "name" in project
            assert "owner_user_id" in project

    @pytest.mark.asyncio
    async def test_get_project(self, client: AsyncClient, auth_headers_user1, project_id):
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_update_project(self, client: AsyncClient, auth_headers_user1, project_id):
        payload = {
            "name": "Updated Name"
        }
        response = await client.put(f"/projects/{project_id}", json=payload, headers=auth_headers_user1)
        assert response.status_code == 204
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_project(self, client: AsyncClient, auth_headers_user1, project_id):
        response = await client.delete(f"/projects/{project_id}", headers=auth_headers_user1)
        assert response.status_code == 204
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user1)
        if response.status_code != 404:
            print(f"GET after delete returned {response.status_code}: {response.text}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_project_forbidden_for_non_owner(self, client: AsyncClient, auth_headers_user1, auth_headers_user2):
        payload = {"name": "User1 Project"}
        response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
        assert response.status_code == 201
        project_id = response.json()["id"]
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user2)
        assert response.status_code in (403, 404)

        response = await client.put(f"/projects/{project_id}", json={"name": "Hacked"}, headers=auth_headers_user2)
        assert response.status_code in (403, 404)

        response = await client.delete(f"/projects/{project_id}", headers=auth_headers_user2)
        assert response.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_get_project_links(self, client: AsyncClient, auth_headers_user1, project_id):
        link_payload = {
            "original_url": "https://example.com",
            "project_id": project_id
        }
        response = await client.post("/links/shorten", json=link_payload, headers=auth_headers_user1)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        response = await client.get(f"/projects/{project_id}/links", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        found = any(item["short_code"] == short_code for item in data)
        assert found

        for item in data:
            assert "short_code" in item
            assert "original_url" in item
            assert "created_at" in item
            assert "expires_at" in item
            assert "clicks" in item
            assert "last_used_at" in item
            assert "owner_user_id" in item
            assert "project_id" in item

    @pytest.mark.asyncio
    async def test_extra_fields_rejected(self, client: AsyncClient, auth_headers_user1):
        payload = {
            "name": "Test",
            "extra": "field"
        }
        response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_extra_fields_rejected_on_update(self, client: AsyncClient, auth_headers_user1, project_id):
        payload = {
            "name": "Updated",
            "extra": "field"
        }
        response = await client.put(f"/projects/{project_id}", json=payload, headers=auth_headers_user1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_uuid_rejected(self, client: AsyncClient, auth_headers_user1):
        invalid_uuid = "not-a-uuid"
        response = await client.get(f"/projects/{invalid_uuid}", headers=auth_headers_user1)
        assert response.status_code == 422

        response = await client.put(f"/projects/{invalid_uuid}", json={"name": "Test"}, headers=auth_headers_user1)
        assert response.status_code == 422

        response = await client.delete(f"/projects/{invalid_uuid}", headers=auth_headers_user1)
        assert response.status_code == 422

        response = await client.get(f"/projects/{invalid_uuid}/links", headers=auth_headers_user1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_pagination_rejected(self, client: AsyncClient, auth_headers_user1, project_id):
        response = await client.get(f"/projects/{project_id}/links", params={"page": 0}, headers=auth_headers_user1)
        assert response.status_code == 422

        response = await client.get(f"/projects/{project_id}/links", params={"size": 101}, headers=auth_headers_user1)
        assert response.status_code == 422

        response = await client.get(f"/projects/{project_id}/links", params={"size": 0}, headers=auth_headers_user1)
        assert response.status_code == 422