import datetime
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.get_project import GetProjectUseCase
from src.application.dto.project_dto import ProjectResponse
from src.application.errors.errors import ProjectNotFoundError, UserNotAuthorizedError
from src.domain.entities.project import Project


class TestGetProjectUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.projects = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return GetProjectUseCase(uow=mock_uow)

    @pytest.fixture
    def sample_project_id(self):
        return uuid4()

    @pytest.fixture
    def sample_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_project(self, sample_project_id, sample_user_id):
        project = Mock(spec=Project)
        project.id = sample_project_id
        project.name = "Test Project"
        project.owner_user_id = sample_user_id
        project.created_at = datetime.datetime.now(datetime.timezone.utc)
        project.updated_at = datetime.datetime.now(datetime.timezone.utc)
        project.is_owner = Mock(return_value=True)
        return project

    async def test_get_project_success(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project):
        """Test successful project retrieval."""
        # Arrange
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

        # Act
        result = await use_case.execute(project_id=sample_project_id, actor_user_id=sample_user_id)

        # Assert
        assert isinstance(result, ProjectResponse)
        assert result.id == sample_project_id
        assert result.name == "Test Project"
        assert result.owner_user_id == sample_user_id
        assert result.created_at == mock_project.created_at
        assert result.updated_at == mock_project.updated_at

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)

    async def test_get_project_not_found(self, use_case, mock_uow, sample_project_id, sample_user_id):
        """Test retrieval fails when project does not exist."""
        # Arrange
        mock_uow.projects.get_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ProjectNotFoundError):
            await use_case.execute(project_id=sample_project_id, actor_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)

    async def test_get_project_not_owner(self, use_case, mock_uow, sample_project_id, sample_user_id):
        """Test retrieval fails when user is not the owner."""
        # Arrange
        mock_project = Mock(spec=Project)
        mock_project.is_owner = Mock(return_value=False)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

        # Act & Assert
        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(project_id=sample_project_id, actor_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)

    async def test_get_project_constructor(self):
        """Test constructor sets uow."""
        # Arrange
        mock_uow = AsyncMock()

        # Act
        use_case = GetProjectUseCase(uow=mock_uow)

        # Assert
        assert use_case._uow is mock_uow