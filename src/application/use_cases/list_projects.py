from uuid import UUID

from ..dto.project_dto import ProjectResponse
from ...domain.repositories.unit_of_work import IUnitOfWork


class ListProjectsUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, owner_user_id: UUID, limit: int = 100, offset: int = 0) -> list[ProjectResponse]:
        projects = await self._uow.projects.list_by_owner(owner_user_id, limit, offset)
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
                owner_user_id=project.owner_user_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            for project in projects
        ]