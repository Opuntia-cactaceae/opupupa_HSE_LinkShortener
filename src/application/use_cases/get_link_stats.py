from datetime import datetime, timezone

from ...domain.value_objects.short_code import ShortCode
from ..dto.link_dto import LinkStatsResponse
from ..errors.errors import LinkNotFoundError, ValidationError
from ...domain.repositories.unit_of_work import IUnitOfWork


class GetLinkStatsUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, short_code: str) -> LinkStatsResponse:
        try:
            code = ShortCode.from_string(short_code)
        except ValueError as e:
            raise ValidationError(str(e))

        link = await self._uow.links.get_by_short_code(str(code))
        if link is None:
            raise LinkNotFoundError()

        stats = await self._uow.stats.get_by_link_id(link.id)
        if stats is None:
            raise LinkNotFoundError()

        from ...infrastructure.settings import settings

        full_short_url = f"{settings.BASE_URL}/{settings.SHORT_LINK_PREFIX}/{link.short_code}"
        is_expired = link.is_expired(datetime.now(timezone.utc))

        return LinkStatsResponse(
            short_code=str(link.short_code),
            original_url=str(link.original_url),
            created_at=link.created_at,
            clicks=stats.clicks,
            last_used_at=stats.last_used_at,
            expires_at=link.expires_at.value if link.expires_at else None,
            full_short_url=full_short_url,
            is_expired=is_expired,
            project_id=link.project_id,
            owner_user_id=link.owner_user_id,
        )