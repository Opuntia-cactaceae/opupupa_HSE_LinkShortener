import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone, timedelta

from src.application.use_cases.list_project_links import ListProjectLinksUseCase
from src.application.dto.link_dto import ProjectLinkResponse
from src.application.errors.errors import ProjectNotFoundError, UserNotAuthorizedError
from src.domain.entities.project import Project
from src.domain.entities.link import Link
from src.domain.entities.link_stats import LinkStats
from src.domain.value_objects.short_code import ShortCode
from src.domain.value_objects.original_url import OriginalUrl
from src.domain.value_objects.expires_at import ExpiresAt


class TestListProjectLinksUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.projects = AsyncMock()
        uow.links = AsyncMock()
        uow.stats = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return ListProjectLinksUseCase(uow=mock_uow)



    @pytest.fixture
    def mock_project(self, sample_project_id, sample_user_id):
        project = Mock(spec=Project)
        project.id = sample_project_id
        project.owner_user_id = sample_user_id
        return project

    @pytest.fixture
    def mock_link(self, sample_project_id, sample_user_id):
        link = Mock(spec=Link)
        link.id = uuid4()
        link.short_code = ShortCode("abc123")
        link.original_url = OriginalUrl("https://example.com")
        link.created_at = datetime.now(timezone.utc)
        link.expires_at = ExpiresAt.from_datetime(datetime.now(timezone.utc) + timedelta(days=1))
        link.expired_at = None
        link.owner_user_id = sample_user_id
        link.project_id = sample_project_id
        return link

    @pytest.fixture
    def mock_stats(self):
        stats = Mock(spec=LinkStats)
        stats.clicks = 10
        stats.last_used_at = datetime.now(timezone.utc)
        return stats

    async def test_list_project_links_success(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project, mock_link, mock_stats):
        
        
        page = 2
        size = 5
        offset = (page - 1) * size  
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_uow.links.find_by_project_id = AsyncMock(return_value=[mock_link])
        mock_uow.stats.get_by_link_ids = AsyncMock(return_value=[mock_stats])
        mock_stats.link_id = mock_link.id

        
        results = await use_case.execute(project_id=sample_project_id, owner_user_id=sample_user_id, page=page, size=size)

        
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ProjectLinkResponse)
        assert result.short_code == "abc123"
        assert result.original_url == "https://example.com"
        assert result.clicks == 10
        assert result.last_used_at == mock_stats.last_used_at
        assert result.owner_user_id == sample_user_id
        assert result.project_id == sample_project_id

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_uow.links.find_by_project_id.assert_called_once_with(sample_project_id, size, offset)
        mock_uow.stats.get_by_link_ids.assert_called_once_with([mock_link.id])

    async def test_list_project_links_project_not_found(self, use_case, mock_uow, sample_project_id, sample_user_id):
        
        
        mock_uow.projects.get_by_id = AsyncMock(return_value=None)

        
        with pytest.raises(ProjectNotFoundError):
            await use_case.execute(project_id=sample_project_id, owner_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_uow.links.find_by_project_id.assert_not_called()

    async def test_list_project_links_unauthorized(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project):
        
        
        other_user_id = uuid4()
        mock_project.owner_user_id = other_user_id  
        mock_project.is_owner = Mock(return_value=False)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

        
        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(project_id=sample_project_id, owner_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)
        mock_uow.links.find_by_project_id.assert_not_called()

    async def test_list_project_links_no_stats(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project, mock_link):
        
        
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_uow.links.find_by_project_id = AsyncMock(return_value=[mock_link])
        mock_uow.stats.get_by_link_ids = AsyncMock(return_value=[])

        
        results = await use_case.execute(project_id=sample_project_id, owner_user_id=sample_user_id)

        
        assert len(results) == 1
        result = results[0]
        assert result.clicks == 0
        assert result.last_used_at is None

    async def test_list_project_links_empty(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project):
        
        
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_uow.links.find_by_project_id = AsyncMock(return_value=[])

        
        results = await use_case.execute(project_id=sample_project_id, owner_user_id=sample_user_id)

        
        assert results == []
        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_uow.links.find_by_project_id.assert_called_once_with(sample_project_id, 20, 0)
        mock_uow.stats.get_by_link_ids.assert_not_called()

    async def test_list_project_links_constructor(self):
        
        
        mock_uow = AsyncMock()

        
        use_case = ListProjectLinksUseCase(uow=mock_uow)

        
        assert use_case._uow is mock_uow