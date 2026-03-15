import pytest
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.delete_project import DeleteProjectUseCase
from src.application.errors.errors import ProjectNotFoundError, UserNotAuthorizedError
from src.domain.entities.project import Project


class TestDeleteProjectUseCase:
    @pytest.fixture
    def mock_uow(self):
        uow = AsyncMock()
        uow.projects = AsyncMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.fixture
    def use_case(self, mock_uow):
        return DeleteProjectUseCase(uow=mock_uow)



    @pytest.fixture
    def mock_project(self, sample_user_id):
        project = Mock(spec=Project)
        project.is_owner = Mock(return_value=True)
        return project

    async def test_delete_project_success(self, use_case, mock_uow, sample_project_id, sample_user_id, mock_project):
        
        
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)
        mock_uow.projects.delete = AsyncMock()
        mock_uow.commit.return_value = None

        
        await use_case.execute(project_id=sample_project_id, actor_user_id=sample_user_id)

        
        mock_uow.projects.get_by_id.assert_called_once_with(sample_project_id)
        mock_project.is_owner.assert_called_once_with(sample_user_id)
        mock_uow.projects.delete.assert_called_once_with(mock_project)
        mock_uow.commit.assert_called_once()

    async def test_delete_project_not_found(self, use_case, mock_uow, sample_project_id, sample_user_id):
        
        
        mock_uow.projects.get_by_id = AsyncMock(return_value=None)

        
        with pytest.raises(ProjectNotFoundError):
            await use_case.execute(project_id=sample_project_id, actor_user_id=sample_user_id)

        
        mock_uow.projects.delete.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_delete_project_not_owner(self, use_case, mock_uow, sample_project_id, sample_user_id):
        
        
        mock_project = Mock(spec=Project)
        mock_project.is_owner = Mock(return_value=False)
        mock_uow.projects.get_by_id = AsyncMock(return_value=mock_project)

        
        with pytest.raises(UserNotAuthorizedError):
            await use_case.execute(project_id=sample_project_id, actor_user_id=sample_user_id)

        
        mock_uow.projects.delete.assert_not_called()
        mock_uow.commit.assert_not_called()

    async def test_delete_project_constructor(self):
        
        
        mock_uow = AsyncMock()

        
        use_case = DeleteProjectUseCase(uow=mock_uow)

        
        assert use_case._uow is mock_uow