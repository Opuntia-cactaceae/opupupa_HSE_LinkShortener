from uuid import UUID

from ..dto.project_dto import UpdateProjectRequest
from ..errors.errors import ProjectNotFoundError, UserNotAuthorizedError, ValidationError
from ...domain.repositories.unit_of_work import IUnitOfWork


class UpdateProjectUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, project_id: UUID, request: UpdateProjectRequest, actor_user_id: UUID) -> None:
        project = await self._uow.projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()

        if not project.is_owner(actor_user_id):
            raise UserNotAuthorizedError()

        try:
            project.update_name(request.name)
        except ValueError as e:
            raise ValidationError(str(e))

        await self._uow.projects.update(project)
        await self._uow.commit()