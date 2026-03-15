import pytest
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
    def sample_project_name(self):
        return "My Project"

    async def test_create_project_success(self, use_case, mock_uow, sample_user_id, sample_project_name):
        request = CreateProjectRequest(name=sample_project_name)
        mock_uow.projects.get_by_name_and_owner = AsyncMock(return_value=None)
        mock_uow.projects.add = AsyncMock()
        mock_uow.commit.return_value = None
        result = await use_case.execute(request, owner_user_id=sample_user_id)
        assert isinstance(result, ProjectResponse)
        assert result.name == sample_project_name
        assert result.owner_user_id == sample_user_id
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None

        
        mock_uow.projects.get_by_name_and_owner.assert_called_once_with(
            sample_project_name, sample_user_id
        )
        mock_uow.projects.add.assert_called_once()
        mock_uow.commit.assert_called_once()
        project_arg = mock_uow.projects.add.call_args[0][0]
        assert isinstance(project_arg, Project)
        assert project_arg.name == sample_project_name
        assert project_arg.owner_user_id == sample_user_id

    async def test_create_project_duplicate_name(self, use_case, mock_uow, sample_user_id, sample_project_name):
        request = CreateProjectRequest(name=sample_project_name)
        existing_project = Mock(spec=Project)
        mock_uow.projects.get_by_name_and_owner = AsyncMock(return_value=existing_project)
        with pytest.raises(ProjectAlreadyExistsError):
            await use_case.execute(request, owner_user_id=sample_user_id)
        mock_uow.projects.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_create_project_validation_error(self, use_case, mock_uow, sample_user_id):
        invalid_name = ""  
        request = CreateProjectRequest(name=invalid_name)
        mock_uow.projects.get_by_name_and_owner = AsyncMock(return_value=None)
        with pytest.raises(ValidationError):
            await use_case.execute(request, owner_user_id=sample_user_id)

        
        mock_uow.projects.add.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_create_project_constructor(self):
        mock_uow = AsyncMock()
        use_case = CreateProjectUseCase(uow=mock_uow)
        assert use_case._uow is mock_uow