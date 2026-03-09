import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import UUID


class TestProjects:
    """Functional tests for projects endpoints."""

    @pytest.fixture
    async def auth_headers_user1(self, client: AsyncClient):
        """Register user1 and return authentication headers."""
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
        """Register user2 and return authentication headers."""
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
        """Create a project and return its ID."""
        payload = {
            "name": "Test Project"
        }
        response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
        assert response.status_code == 201
        data = response.json()
        return data["id"]

    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers_user1):
        """POST /projects should create a project."""
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
        # Ensure owner_user_id matches authenticated user (we can't easily verify)
        # but we can check it's a valid UUID
        try:
            UUID(data["owner_user_id"])
        except ValueError:
            pytest.fail("owner_user_id is not a valid UUID")

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers_user1):
        """GET /projects should return user's projects."""
        # Create two projects
        for i in range(2):
            payload = {"name": f"Project {i}"}
            response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
            assert response.status_code == 201
        # List projects
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
        """GET /projects/{project_id} should return project details."""
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_update_project(self, client: AsyncClient, auth_headers_user1, project_id):
        """PUT /projects/{project_id} should update project."""
        payload = {
            "name": "Updated Name"
        }
        response = await client.put(f"/projects/{project_id}", json=payload, headers=auth_headers_user1)
        assert response.status_code == 204
        # Verify update
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_project(self, client: AsyncClient, auth_headers_user1, project_id):
        """DELETE /projects/{project_id} should delete project."""
        response = await client.delete(f"/projects/{project_id}", headers=auth_headers_user1)
        assert response.status_code == 204
        # Verify deleted
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user1)
        if response.status_code != 404:
            print(f"GET after delete returned {response.status_code}: {response.text}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_project_forbidden_for_non_owner(self, client: AsyncClient, auth_headers_user1, auth_headers_user2):
        """Operations on another user's project should fail."""
        # User1 creates a project
        payload = {"name": "User1 Project"}
        response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
        assert response.status_code == 201
        project_id = response.json()["id"]
        # User2 attempts to get project
        response = await client.get(f"/projects/{project_id}", headers=auth_headers_user2)
        assert response.status_code in (403, 404)  # Not found (or 403 depending on implementation)
        # User2 attempts to update
        response = await client.put(f"/projects/{project_id}", json={"name": "Hacked"}, headers=auth_headers_user2)
        assert response.status_code in (403, 404)
        # User2 attempts to delete
        response = await client.delete(f"/projects/{project_id}", headers=auth_headers_user2)
        assert response.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_get_project_links(self, client: AsyncClient, auth_headers_user1, project_id):
        """GET /projects/{project_id}/links should return links belonging to project."""
        # Create a link associated with the project
        link_payload = {
            "original_url": "https://example.com",
            "project_id": project_id
        }
        response = await client.post("/links/shorten", json=link_payload, headers=auth_headers_user1)
        assert response.status_code == 201
        short_code = response.json()["short_code"]
        # Get project links
        response = await client.get(f"/projects/{project_id}/links", headers=auth_headers_user1)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should contain at least the created link
        found = any(item["short_code"] == short_code for item in data)
        assert found
        # Check structure
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
        """Extra fields in project requests should be rejected."""
        payload = {
            "name": "Test",
            "extra": "field"
        }
        response = await client.post("/projects/", json=payload, headers=auth_headers_user1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_extra_fields_rejected_on_update(self, client: AsyncClient, auth_headers_user1, project_id):
        """Extra fields in project update request should be rejected."""
        payload = {
            "name": "Updated",
            "extra": "field"
        }
        response = await client.put(f"/projects/{project_id}", json=payload, headers=auth_headers_user1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_uuid_rejected(self, client: AsyncClient, auth_headers_user1):
        """Invalid UUID in path parameters should be rejected."""
        invalid_uuid = "not-a-uuid"
        # GET /projects/{project_id}
        response = await client.get(f"/projects/{invalid_uuid}", headers=auth_headers_user1)
        assert response.status_code == 422
        # PUT /projects/{project_id}
        response = await client.put(f"/projects/{invalid_uuid}", json={"name": "Test"}, headers=auth_headers_user1)
        assert response.status_code == 422
        # DELETE /projects/{project_id}
        response = await client.delete(f"/projects/{invalid_uuid}", headers=auth_headers_user1)
        assert response.status_code == 422
        # GET /projects/{project_id}/links
        response = await client.get(f"/projects/{invalid_uuid}/links", headers=auth_headers_user1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_pagination_rejected(self, client: AsyncClient, auth_headers_user1, project_id):
        """Invalid pagination parameters should be rejected."""
        # Page less than 1
        response = await client.get(f"/projects/{project_id}/links", params={"page": 0}, headers=auth_headers_user1)
        assert response.status_code == 422
        # Size greater than max (max is 100 per schema? actually size le=100)
        response = await client.get(f"/projects/{project_id}/links", params={"size": 101}, headers=auth_headers_user1)
        assert response.status_code == 422
        # Size less than 1
        response = await client.get(f"/projects/{project_id}/links", params={"size": 0}, headers=auth_headers_user1)
        assert response.status_code == 422