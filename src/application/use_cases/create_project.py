from uuid import UUID

from ..dto.project_dto import ProjectResponse, CreateProjectRequest
from ..errors.errors import ProjectAlreadyExistsError, ValidationError
from ...domain.entities.project import Project
from ...domain.repositories.unit_of_work import IUnitOfWork


class CreateProjectUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        request: CreateProjectRequest,
        owner_user_id: UUID,
    ) -> ProjectResponse:
        try:
            project = Project.create(request.name, owner_user_id)
        except ValueError as e:
            raise ValidationError(str(e))

        existing_project = await self._uow.projects.get_by_name_and_owner(
            project.name,
            owner_user_id,
        )
        if existing_project is not None:
            raise ProjectAlreadyExistsError()

        await self._uow.projects.add(project)
        await self._uow.commit()

        return ProjectResponse(
            id=project.id,
            name=project.name,
            owner_user_id=project.owner_user_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )