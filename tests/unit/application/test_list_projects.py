import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from src.application.use_cases.list_projects import ListProjectsUseCase
from src.application.dto.project_dto import ProjectResponse
from src.domain.entities.project import Project


class TestListProjectsUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.projects = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return ListProjectsUseCase(uow=mock_uow)


    @pytest.fixture
    def mock_project(self, sample_user_id):
        project = Mock(spec=Project)
        project.id = uuid4()
        project.name = "Test Project"
        project.owner_user_id = sample_user_id
        project.created_at = datetime.now(timezone.utc)
        project.updated_at = datetime.now(timezone.utc)
        return project

    async def test_list_projects_success(self, use_case, mock_uow, sample_user_id, mock_project):
        
        
        limit = 50
        offset = 10
        mock_uow.projects.list_by_owner = AsyncMock(return_value=[mock_project])

        
        results = await use_case.execute(owner_user_id=sample_user_id, limit=limit, offset=offset)

        
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ProjectResponse)
        assert result.id == mock_project.id
        assert result.name == "Test Project"
        assert result.owner_user_id == sample_user_id
        assert result.created_at == mock_project.created_at
        assert result.updated_at == mock_project.updated_at

        mock_uow.projects.list_by_owner.assert_called_once_with(sample_user_id, limit, offset)

    async def test_list_projects_empty(self, use_case, mock_uow, sample_user_id):
        
        
        mock_uow.projects.list_by_owner = AsyncMock(return_value=[])

        
        results = await use_case.execute(owner_user_id=sample_user_id)

        
        assert results == []
        mock_uow.projects.list_by_owner.assert_called_once_with(sample_user_id, 100, 0)

    async def test_list_projects_default_parameters(self, use_case, mock_uow, sample_user_id, mock_project):
        
        
        mock_uow.projects.list_by_owner = AsyncMock(return_value=[mock_project])

        
        results = await use_case.execute(owner_user_id=sample_user_id)

        
        assert len(results) == 1
        mock_uow.projects.list_by_owner.assert_called_once_with(sample_user_id, 100, 0)

    async def test_list_projects_constructor(self):
        
        
        mock_uow = AsyncMock()

        
        use_case = ListProjectsUseCase(uow=mock_uow)

        
        assert use_case._uow is mock_uow