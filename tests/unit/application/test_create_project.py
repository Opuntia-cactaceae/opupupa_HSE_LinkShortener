import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.create_project import CreateProjectUseCase
from src.application.dto.project_dto import CreateProjectRequest, ProjectResponse
from src.application.errors.errors import ProjectAlreadyExistsError, ValidationError
from src.domain.entities.project import Project


class TestCreateProjectUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.projects = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return CreateProjectUseCase(uow=mock_uow)

    @pytest.fixture
    def sample_user_id(self):
        return uuid4()

    @pytest.fixture
    def sample_project_name(self):
        return "My Project"

    async def test_create_project_success(self, use_case, mock_uow, sample_user_id, sample_project_name):
        """Test successful project creation."""
        # Arrange
        request = CreateProjectRequest(name=sample_project_name)
        mock_uow.projects.get_by_name_and_owner = AsyncMock(return_value=None)
        mock_uow.projects.add = AsyncMock()
        mock_uow.commit.return_value = None

        # Act
        result = await use_case.execute(request, owner_user_id=sample_user_id)

        # Assert
        assert isinstance(result, ProjectResponse)
        assert result.name == sample_project_name
        assert result.owner_user_id == sample_user_id
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None

        # Verify interactions
        mock_uow.projects.get_by_name_and_owner.assert_called_once_with(
            sample_project_name, sample_user_id
        )
        mock_uow.projects.add.assert_called_once()
        mock_uow.commit.assert_called_once()

        # Verify the created project
        project_arg = mock_uow.projects.add.call_args[0][0]
        assert isinstance(project_arg, Project)
        assert project_arg.name == sample_project_name
        assert project_arg.owner_user_id == sample_user_id

    async def test_create_project_duplicate_name(self, use_case, mock_uow, sample_user_id, sample_project_name):
        """Test project creation fails when project with same name exists for same owner."""
        # Arrange
        request = CreateProjectRequest(name=sample_project_name)
        existing_project = Mock(spec=Project)
        mock_uow.projects.get_by_name_and_owner = AsyncMock(return_value=existing_project)

        # Act & Assert
        with pytest.raises(ProjectAlreadyExistsError):
            await use_case.execute(request, owner_user_id=sample_user_id)

        # Verify no addition or commit
        mock_uow.projects.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_create_project_validation_error(self, use_case, mock_uow, sample_user_id):
        """Test project creation fails with invalid name."""
        # Arrange
        invalid_name = ""  # empty name should raise ValueError in Project.create
        request = CreateProjectRequest(name=invalid_name)
        mock_uow.projects.get_by_name_and_owner = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValidationError):
            await use_case.execute(request, owner_user_id=sample_user_id)

        # Verify no addition or commit
        mock_uow.projects.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_create_project_constructor(self):
        """Test constructor sets uow."""
        # Arrange
        mock_uow = AsyncMock()

        # Act
        use_case = CreateProjectUseCase(uow=mock_uow)

        # Assert
        assert use_case._uow is mock_uow