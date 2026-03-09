from typing import Optional
from uuid import UUID

from ..dto.link_dto import ProjectLinkResponse
from ..errors.errors import ProjectNotFoundError, UserNotAuthorizedError
from ...domain.repositories.unit_of_work import IUnitOfWork


class ListProjectLinksUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        project_id: UUID,
        owner_user_id: UUID,
        page: int = 1,
        size: int = 20,
    ) -> list[ProjectLinkResponse]:
        offset = (page - 1) * size

        project = await self._uow.projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError()

        if not project.is_owner(owner_user_id):
            raise UserNotAuthorizedError()

        links = await self._uow.links.find_by_project_id(project_id, size, offset)

        link_ids = [link.id for link in links]
        if link_ids:
            stats_list = await self._uow.stats.get_by_link_ids(link_ids)
            stats_by_link_id = {stats.link_id: stats for stats in stats_list}
        else:
            stats_by_link_id = {}

        results = []
        for link in links:
            stats = stats_by_link_id.get(link.id)
            clicks = stats.clicks if stats else 0
            last_used_at = stats.last_used_at if stats else None
            results.append(
                ProjectLinkResponse(
                    short_code=str(link.short_code),
                    original_url=str(link.original_url),
                    created_at=link.created_at,
                    expires_at=link.expires_at.value if link.expires_at else None,
                    expired_at=link.expired_at,
                    clicks=clicks,
                    last_used_at=last_used_at,
                    owner_user_id=link.owner_user_id,
                    project_id=link.project_id,
                )
            )
        return results