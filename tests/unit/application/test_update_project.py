import pytest
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.update_project import UpdateProjectUseCase
from src.application.dto.project_dto import UpdateProjectRequest
from src.application.errors.errors import ProjectNotFoundError, UserNotAuthorizedError, ValidationError
from src.domain.entities.project import Project


class TestUpdateProjectUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.projects = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return UpdateProjectUseCase(uow=mock_uow)

    @pytest.fixture
    def mock_project(self, sample_user_id):
        project = Mock(spec=Project)
        project.is_owner = Mock(return_value=True)
        project.update_name = Mock()
        return project

    async def test_update_project_success(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project):
        new_name = "Updated Project Name"
        request = UpdateProjectRequest(name=new_name)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_uow.projects.update = AsyncMock()
        mock_uow.commit.return_value = None

        await use_case.execute(project_id=sample_project_id, request=request, actor_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)
        mock_project.update_name.assert_called_once_with(new_name)
        mock_uow.projects.update.assert_called_once_with(mock_project)
        mock_uow.commit.assert_called_once()

    async def test_update_project_not_found(self, use_case, mock_uow, sample_project_id, sample_user_id):
        request = UpdateProjectRequest(name="New Name")
        mock_uow.projects.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ProjectNotFoundError):
            await use_case.execute(project_id=sample_project_id, request=request, actor_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_uow.projects.update.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_update_project_unauthorized(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project):
        mock_project.is_owner = Mock(return_value=False)
        request = UpdateProjectRequest(name="New Name")
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(project_id=sample_project_id, request=request, actor_user_id=sample_user_id)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)
        mock_project.update_name.assert_not_called()
        mock_uow.projects.update.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_update_project_validation_error(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project):
        invalid_name = ""  
        request = UpdateProjectRequest(name=invalid_name)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_project.update_name.side_effect = ValueError("Name cannot be empty")

        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(project_id=sample_project_id, request=request, actor_user_id=sample_user_id)

        assert "Name cannot be empty" in str(exc_info.value)

        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)
        mock_project.update_name.assert_called_once_with(invalid_name)
        mock_uow.projects.update.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_update_project_constructor(self):
        mock_uow = AsyncMock()
        use_case = UpdateProjectUseCase(uow=mock_uow)
        assert use_case._uow is mock_uow