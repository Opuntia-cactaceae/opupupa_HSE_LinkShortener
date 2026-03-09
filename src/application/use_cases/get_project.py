from uuid import UUID

from ..dto.project_dto import ProjectResponse
from ..errors.errors import ProjectNotFoundError, UserNotAuthorizedError
from ...domain.repositories.unit_of_work import IUnitOfWork


class GetProjectUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, project_id: UUID, actor_user_id: UUID) -> ProjectResponse:
        project = await self._uow.projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()

        if not project.is_owner(actor_user_id):
            raise UserNotAuthorizedError()

        return ProjectResponse(
            id=project.id,
            name=project.name,
            owner_user_id=project.owner_user_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )