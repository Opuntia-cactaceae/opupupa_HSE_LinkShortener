import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.search_link_by_original_url import SearchLinkByOriginalUrlUseCase
from src.application.dto.link_dto import LinkInfoResponse, SearchLinksQuery
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


class TestSearchLinkByOriginalUrlUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return SearchLinkByOriginalUrlUseCase(uow=mock_uow)

    @pytest.fixture
    def sample_original_url(self):
        return "https://example.com"

    @pytest.fixture
    def sample_link(self):
        link = Mock()
        link.id = uuid4()
        link.short_code = Mock(spec=ShortCode)
        link.short_code.value = "abc123"
        link.short_code.__str__ = Mock(return_value="abc123")
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.value = "https://example.com"
        link.original_url.__str__ = Mock(return_value="https://example.com")
        link.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        link.updated_at = datetime.now(timezone.utc)
        link.expires_at = None
        link.owner_user_id = uuid4()
        link.is_deleted = False
        link.is_expired = Mock(return_value=False)
        return link

    async def test_successful_search(
        self,
        use_case,
        mock_uow,
        sample_original_url,
        sample_link,
    ):
        
        
        mock_uow.links.find_by_original_url = AsyncMock(return_value=[sample_link])
        query = SearchLinksQuery(original_url=sample_original_url)

        
        results = await use_case.execute(query)

        
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, LinkInfoResponse)
        assert result.short_code == "abc123"
        assert result.original_url == "https://example.com"
        assert result.created_at == sample_link.created_at
        assert result.updated_at == sample_link.updated_at
        assert result.expires_at is None
        assert result.owner_user_id == sample_link.owner_user_id
        assert result.is_deleted is False

        
        mock_uow.links.find_by_original_url.assert_called_once_with(
            sample_original_url, 100, 0
        )

    async def test_empty_result(
        self,
        use_case,
        mock_uow,
        sample_original_url,
    ):
        
        
        mock_uow.links.find_by_original_url = AsyncMock(return_value=[])
        query = SearchLinksQuery(original_url=sample_original_url)

        
        results = await use_case.execute(query)

        
        assert results == []
        mock_uow.links.find_by_original_url.assert_called_once_with(
            sample_original_url, 100, 0
        )

    async def test_pagination(
        self,
        use_case,
        mock_uow,
        sample_original_url,
    ):
        
        
        mock_uow.links.find_by_original_url = AsyncMock(return_value=[])
        query = SearchLinksQuery(original_url=sample_original_url, limit=10, offset=20)

        
        await use_case.execute(query)

        
        mock_uow.links.find_by_original_url.assert_called_once_with(
            sample_original_url, 10, 20
        )

    async def test_multiple_links(
        self,
        use_case,
        mock_uow,
        sample_original_url,
        sample_link,
    ):
        
        
        link2 = Mock()
        link2.short_code = Mock(spec=ShortCode)
        link2.short_code.__str__ = Mock(return_value="def456")
        link2.original_url = Mock(spec=OriginalUrl)
        link2.original_url.__str__ = Mock(return_value="https://example.com")
        link2.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        link2.updated_at = datetime.now(timezone.utc)
        link2.expires_at = None
        link2.owner_user_id = uuid4()
        link2.is_deleted = False

        mock_uow.links.find_by_original_url = AsyncMock(return_value=[sample_link, link2])
        query = SearchLinksQuery(original_url=sample_original_url)

        
        results = await use_case.execute(query)

        
        assert len(results) == 2
        assert results[0].short_code == "abc123"
        assert results[1].short_code == "def456"

    async def test_link_with_expiration(
        self,
        use_case,
        mock_uow,
        sample_original_url,
    ):
        
        
        link = Mock()
        link.short_code = Mock(spec=ShortCode)
        link.short_code.__str__ = Mock(return_value="abc123")
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.__str__ = Mock(return_value="https://example.com")
        link.created_at = datetime.now(timezone.utc)
        link.updated_at = datetime.now(timezone.utc)
        expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        link.expires_at = Mock(spec=ExpiresAt)
        link.expires_at.value = expires_at
        link.owner_user_id = uuid4()
        link.is_deleted = False

        mock_uow.links.find_by_original_url = AsyncMock(return_value=[link])
        query = SearchLinksQuery(original_url=sample_original_url)

        
        results = await use_case.execute(query)

        
        assert results[0].expires_at == expires_at

    async def test_link_deleted(
        self,
        use_case,
        mock_uow,
        sample_original_url,
    ):
        
        
        link = Mock()
        link.short_code = Mock(spec=ShortCode)
        link.short_code.__str__ = Mock(return_value="abc123")
        link.original_url = Mock(spec=OriginalUrl)
        link.original_url.__str__ = Mock(return_value="https://example.com")
        link.created_at = datetime.now(timezone.utc)
        link.updated_at = datetime.now(timezone.utc)
        link.expires_at = None
        link.owner_user_id = uuid4()
        link.is_deleted = True

        mock_uow.links.find_by_original_url = AsyncMock(return_value=[link])
        query = SearchLinksQuery(original_url=sample_original_url)

        
        results = await use_case.execute(query)

        
        assert results[0].is_deleted is True