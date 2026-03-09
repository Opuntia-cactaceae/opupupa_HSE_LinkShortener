from datetime import datetime, timezone

from ..dto.link_dto import LinkInfoResponse, SearchLinksQuery
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.settings import settings


class SearchLinkByOriginalUrlUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: SearchLinksQuery) -> list[LinkInfoResponse]:
        links = await self._uow.links.find_by_original_url(
            query.original_url, query.limit, query.offset
        )

        # Load stats in batch
        link_ids = [link.id for link in links]
        if link_ids:
            stats_list = await self._uow.stats.get_by_link_ids(link_ids)
            stats_by_link_id = {stats.link_id: stats for stats in stats_list}
        else:
            stats_by_link_id = {}

        now = datetime.now(timezone.utc)
        base_url = settings.BASE_URL
        prefix = settings.SHORT_LINK_PREFIX

        results = []
        for link in links:
            stats = stats_by_link_id.get(link.id)
            clicks = stats.clicks if stats else 0
            last_used_at = stats.last_used_at if stats else None
            results.append(
                LinkInfoResponse(
                    short_code=str(link.short_code),
                    original_url=str(link.original_url),
                    created_at=link.created_at,
                    updated_at=link.updated_at,
                    expires_at=link.expires_at.value if link.expires_at else None,
                    owner_user_id=link.owner_user_id,
                    is_deleted=link.is_deleted,
                    full_short_url=f"{base_url}/{prefix}/{link.short_code}",
                    is_expired=link.is_expired(now),
                    project_id=link.project_id,
                    clicks=clicks,
                    last_used_at=last_used_at,
                )
            )
        return results