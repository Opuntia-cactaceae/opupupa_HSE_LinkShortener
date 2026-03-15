import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.project import ProjectModel
from src.infrastructure.db.models.link import LinkModel


class TestProjectsFlow:
    

    @pytest.fixture
    async def auth_headers_a(self, client: AsyncClient) -> dict:
        
        unique_email = f"projuser_a_{uuid.uuid4().hex[:8]}@example.com"

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
        
        unique_email = f"projuser_b_{uuid.uuid4().hex[:8]}@example.com"

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
    async def test_create_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        response = await client.post(
            "/projects/",
            json={"name": "Test Project"},
            headers=auth_headers_a,
        )
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Project"
        assert "owner_user_id" in data
        assert "created_at" in data
        assert "updated_at" in data

        project_id = data["id"]
        owner_user_id = data["owner_user_id"]

        db_session.expire_all()
        stmt = select(ProjectModel).where(ProjectModel.id == uuid.UUID(project_id))
        result = await db_session.execute(stmt)
        project = result.scalar_one_or_none()

        assert project is not None
        assert project.name == "Test Project"
        assert str(project.owner_user_id) == owner_user_id

    @pytest.mark.asyncio
    async def test_list_user_projects(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        project_names = ["Project One", "Project Two", "Project Three"]
        created_ids = []

        for name in project_names:
            response = await client.post(
                "/projects/",
                json={"name": name},
                headers=auth_headers_a,
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        response = await client.get("/projects/", headers=auth_headers_a)
        assert response.status_code == 200

        projects = response.json()
        assert isinstance(projects, list)
        assert len(projects) == len(project_names)

        returned_ids = {p["id"] for p in projects}
        assert returned_ids == set(created_ids)

        for project in projects:
            assert "id" in project
            assert "name" in project
            assert "owner_user_id" in project
            assert "created_at" in project
            assert "updated_at" in project

        db_session.expire_all()
        stmt = select(func.count()).select_from(ProjectModel)
        result = await db_session.execute(stmt)
        db_count = result.scalar()
        assert db_count == len(project_names)

    @pytest.mark.asyncio
    async def test_project_ownership(
        self,
        client: AsyncClient,
        auth_headers_a,
        auth_headers_b,
    ):
        
        response = await client.post(
            "/projects/",
            json={"name": "User A Project"},
            headers=auth_headers_a,
        )
        assert response.status_code == 201

        project_id = response.json()["id"]

        response = await client.get(f"/projects/{project_id}", headers=auth_headers_b)
        assert response.status_code in (403, 404)

        response = await client.get(f"/projects/{project_id}", headers=auth_headers_a)
        assert response.status_code == 200

        owner_data = response.json()
        assert owner_data["id"] == project_id
        assert owner_data["name"] == "User A Project"

    @pytest.mark.asyncio
    async def test_update_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        create_response = await client.post(
            "/projects/",
            json={"name": "Original Name"},
            headers=auth_headers_a,
        )
        assert create_response.status_code == 201

        project_id = create_response.json()["id"]

        update_response = await client.put(
            f"/projects/{project_id}",
            json={"name": "Updated Name"},
            headers=auth_headers_a,
        )
        assert update_response.status_code == 204

        db_session.expire_all()
        stmt = select(ProjectModel).where(ProjectModel.id == uuid.UUID(project_id))
        result = await db_session.execute(stmt)
        project = result.scalar_one_or_none()

        assert project is not None
        assert project.name == "Updated Name"

        get_response = await client.get(f"/projects/{project_id}", headers=auth_headers_a)
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        create_response = await client.post(
            "/projects/",
            json={"name": "Project to Delete"},
            headers=auth_headers_a,
        )
        assert create_response.status_code == 201

        project_id = create_response.json()["id"]

        stmt = select(ProjectModel).where(ProjectModel.id == uuid.UUID(project_id))
        db_session.expire_all()
        result = await db_session.execute(stmt)
        project_before = result.scalar_one_or_none()
        assert project_before is not None

        delete_response = await client.delete(
            f"/projects/{project_id}",
            headers=auth_headers_a,
        )
        assert delete_response.status_code == 204

        db_session.expire_all()
        result = await db_session.execute(stmt)
        project_after = result.scalar_one_or_none()
        assert project_after is None

    @pytest.mark.asyncio
    async def test_list_project_links(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers_a,
    ):
        
        project_response = await client.post(
            "/projects/",
            json={"name": "Link Collection"},
            headers=auth_headers_a,
        )
        assert project_response.status_code == 201

        project_id = project_response.json()["id"]

        link_urls = [
            "https://project-link1.example.com",
            "https://project-link2.example.com",
            "https://project-link3.example.com",
        ]
        created_short_codes = []

        for url in link_urls:
            response = await client.post(
                "/links/shorten",
                json={"original_url": url, "project_id": project_id},
                headers=auth_headers_a,
            )
            assert response.status_code == 201
            created_short_codes.append(response.json()["short_code"])

        links_response = await client.get(
            f"/projects/{project_id}/links",
            headers=auth_headers_a,
        )
        assert links_response.status_code == 200

        links_data = links_response.json()
        assert isinstance(links_data, list)
        assert len(links_data) == len(link_urls)

        returned_short_codes = set()
        for link in links_data:
            assert link["project_id"] == project_id
            assert link["short_code"] in created_short_codes
            returned_short_codes.add(link["short_code"])

        assert returned_short_codes == set(created_short_codes)

        db_session.expire_all()
        stmt = select(func.count()).select_from(LinkModel).where(
            LinkModel.project_id == uuid.UUID(project_id)
        )
        result = await db_session.execute(stmt)
        db_count = result.scalar()
        assert db_count == len(link_urls)