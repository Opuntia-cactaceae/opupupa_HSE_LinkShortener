import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.link import LinkModel


class TestSearchAndDiscovery:
    

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict:
        
        unique_email = f"searchuser_{uuid.uuid4().hex[:8]}@example.com"

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
    async def test_search_returns_matching_links(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        urls_to_create = [
            "https://search.example.com",
            "https://other.example.com",
            "https://search.example.com",
            "https://another.example.com",
        ]
        created_links = []
        normalized_search_url = None

        for url in urls_to_create:
            response = await client.post("/links/shorten", json={"original_url": url})
            assert response.status_code == 201

            data = response.json()
            created_links.append((data["short_code"], data["original_url"]))

            if url == "https://search.example.com" and normalized_search_url is None:
                normalized_search_url = data["original_url"]

        assert normalized_search_url == "https://search.example.com/"

        search_response = await client.get(
            "/links/search",
            params={"original_url": normalized_search_url},
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        assert "items" in search_data
        assert "page" in search_data
        assert "size" in search_data
        assert search_data["page"] == 1
        assert search_data["size"] == 100

        items = search_data["items"]
        assert len(items) == 2

        returned_short_codes = set()
        for item in items:
            assert item["original_url"] == normalized_search_url
            returned_short_codes.add(item["short_code"])

        expected_codes = {
            code for code, norm_url in created_links if norm_url == normalized_search_url
        }
        assert returned_short_codes == expected_codes

        db_session.expire_all()
        stmt = select(func.count()).select_from(LinkModel).where(
            LinkModel.original_url == normalized_search_url
        )
        result = await db_session.execute(stmt)
        db_count = result.scalar()
        assert db_count == 2

    @pytest.mark.asyncio
    async def test_search_returns_empty_list(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        urls = [
            "https://exists1.example.com",
            "https://exists2.example.com",
        ]
        for url in urls:
            response = await client.post("/links/shorten", json={"original_url": url})
            assert response.status_code == 201

        search_response = await client.get(
            "/links/search",
            params={"original_url": "https://nonexistent.example.com"},
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        assert search_data["items"] == []
        assert search_data["page"] == 1
        assert search_data["size"] == 100

    @pytest.mark.asyncio
    async def test_pagination_works(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        base_url = "https://pagination.example.com"
        total_links = 5

        created_links = []
        normalized_url = None

        for i in range(total_links):
            response = await client.post("/links/shorten", json={"original_url": base_url})
            assert response.status_code == 201

            data = response.json()
            created_links.append((data["short_code"], data["original_url"]))
            if i == 0:
                normalized_url = data["original_url"]

        assert normalized_url == "https://pagination.example.com/"

        search_response = await client.get(
            "/links/search",
            params={
                "original_url": normalized_url,
                "page": 1,
                "size": 2,
            },
        )
        assert search_response.status_code == 200
        page1_data = search_response.json()
        assert len(page1_data["items"]) == 2
        assert page1_data["page"] == 1
        assert page1_data["size"] == 2

        search_response = await client.get(
            "/links/search",
            params={
                "original_url": normalized_url,
                "page": 2,
                "size": 2,
            },
        )
        assert search_response.status_code == 200
        page2_data = search_response.json()
        assert len(page2_data["items"]) == 2
        assert page2_data["page"] == 2
        assert page2_data["size"] == 2

        search_response = await client.get(
            "/links/search",
            params={
                "original_url": normalized_url,
                "page": 3,
                "size": 2,
            },
        )
        assert search_response.status_code == 200
        page3_data = search_response.json()
        assert len(page3_data["items"]) == 1
        assert page3_data["page"] == 3
        assert page3_data["size"] == 2

        page1_codes = {item["short_code"] for item in page1_data["items"]}
        page2_codes = {item["short_code"] for item in page2_data["items"]}
        page3_codes = {item["short_code"] for item in page3_data["items"]}

        assert page1_codes.isdisjoint(page2_codes)
        assert page1_codes.isdisjoint(page3_codes)
        assert page2_codes.isdisjoint(page3_codes)

        all_returned_codes = page1_codes | page2_codes | page3_codes
        all_created_codes = {code for code, _ in created_links}
        assert all_returned_codes == all_created_codes

    @pytest.mark.asyncio
    async def test_invalid_query_returns_validation_error(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        
        search_response = await client.get("/links/search")
        assert search_response.status_code in (400, 422)

        search_response = await client.get(
            "/links/search",
            params={"original_url": "not-a-valid-url"},
        )
        assert search_response.status_code in (400, 422)
        data = search_response.json()
        assert "detail" in data
