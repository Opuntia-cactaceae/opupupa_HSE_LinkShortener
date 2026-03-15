import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from src.application.use_cases.list_expired_links import ListExpiredLinksUseCase
from src.application.dto.link_dto import ExpiredLinksResponse
from src.domain.entities.link import Link
from src.domain.entities.link_stats import LinkStats
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl


class TestListExpiredLinksUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.links = AsyncMock()
        uow.stats = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return ListExpiredLinksUseCase(uow=mock_uow)


    @pytest.fixture
    def sample_link(self, sample_user_id):
        link = Mock(spec=Link)
        link.id = uuid4()
        link.short_code = ShortCode("expired123")
        link.original_url = OriginalUrl("https://example.com")
        link.created_at = datetime.now(timezone.utc)
        link.expired_at = datetime.now(timezone.utc)  
        link.owner_user_id = sample_user_id
        link.project_id = None
        return link

    @pytest.fixture
    def sample_stats(self, sample_link):
        stats = Mock(spec=LinkStats)
        stats.clicks = 42
        stats.last_used_at = datetime.now(timezone.utc)
        return stats

    async def test_list_expired_links_with_owner(self, use_case, mock_uow, sample_user_id, sample_link, sample_stats):
        
        
        page = 2
        size = 10
        offset = (page - 1) * size  
        mock_uow.links.list_expired_history = AsyncMock(return_value=[sample_link])
        mock_uow.stats.get_by_link_ids = AsyncMock(return_value=[sample_stats])
        sample_stats.link_id = sample_link.id

        
        results = await use_case.execute(owner_user_id=sample_user_id, page=page, size=size)

        
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExpiredLinksResponse)
        assert result.short_code == "expired123"
        assert result.original_url == "https://example.com"
        assert result.clicks == 42
        assert result.last_used_at == sample_stats.last_used_at
        assert result.owner_user_id == sample_user_id
        assert result.project_id is None

        mock_uow.links.list_expired_history.assert_called_once_with(sample_user_id, size, offset)
        mock_uow.stats.get_by_link_ids.assert_called_once_with([sample_link.id])

    async def test_list_expired_links_without_owner(self, use_case, mock_uow, sample_link, sample_stats):
        
        
        mock_uow.links.list_expired_history = AsyncMock(return_value=[sample_link])
        mock_uow.stats.get_by_link_ids = AsyncMock(return_value=[sample_stats])
        sample_stats.link_id = sample_link.id

        
        results = await use_case.execute(owner_user_id=None, page=1, size=20)

        
        assert len(results) == 1
        mock_uow.links.list_expired_history.assert_called_once_with(None, 20, 0)
        mock_uow.stats.get_by_link_ids.assert_called_once_with([sample_link.id])

    async def test_list_expired_links_no_stats(self, use_case, mock_uow, sample_user_id, sample_link):
        
        
        mock_uow.links.list_expired_history = AsyncMock(return_value=[sample_link])
        mock_uow.stats.get_by_link_ids = AsyncMock(return_value=[])

        
        results = await use_case.execute(owner_user_id=sample_user_id)

        
        assert len(results) == 1
        result = results[0]
        assert result.clicks == 0
        assert result.last_used_at is None

    async def test_list_expired_links_empty(self, use_case, mock_uow, sample_user_id):
        
        
        mock_uow.links.list_expired_history = AsyncMock(return_value=[])
        

        
        results = await use_case.execute(owner_user_id=sample_user_id)

        
        assert results == []
        mock_uow.links.list_expired_history.assert_called_once_with(sample_user_id, 20, 0)
        mock_uow.stats.get_by_link_id.assert_not_called()

    async def test_list_expired_links_constructor(self):
        
        
        mock_uow = AsyncMock()

        
        use_case = ListExpiredLinksUseCase(uow=mock_uow)

        
        assert use_case._uow is mock_uow