from uuid import UUID

from ..errors.errors import ProjectNotFoundError, UserNotAuthorizedError
from ...domain.repositories.unit_of_work import IUnitOfWork


class DeleteProjectUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, project_id: UUID, actor_user_id: UUID) -> None:
        project = await self._uow.projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()

        if not project.is_owner(actor_user_id):
            raise UserNotAuthorizedError()

        await self._uow.projects.delete(project)
        await self._uow.commit()