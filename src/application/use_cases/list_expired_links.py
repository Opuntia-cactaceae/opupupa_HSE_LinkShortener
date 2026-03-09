from typing import Optional
from uuid import UUID

from ..dto.link_dto import ExpiredLinksResponse
from ...domain.repositories.unit_of_work import IUnitOfWork


class ListExpiredLinksUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, owner_user_id: Optional[UUID], page: int = 1, size: int = 20
    ) -> list[ExpiredLinksResponse]:
        offset = (page - 1) * size
        links = await self._uow.links.list_expired_history(owner_user_id, size, offset)

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
                ExpiredLinksResponse(
                    short_code=str(link.short_code),
                    original_url=str(link.original_url),
                    created_at=link.created_at,
                    expired_at=link.expired_at,
                    clicks=clicks,
                    last_used_at=last_used_at,
                    owner_user_id=link.owner_user_id,
                    project_id=link.project_id,
                )
            )
        return results