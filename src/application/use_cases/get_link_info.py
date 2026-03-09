from datetime import datetime, timezone

from ...domain.value_objects.short_code import ShortCode
from ..dto.link_dto import LinkInfoResponse
from ..errors.errors import LinkNotFoundError, ValidationError
from ...domain.repositories.unit_of_work import IUnitOfWork


class GetLinkInfoUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, short_code: str) -> LinkInfoResponse:
        try:
            code = ShortCode.from_string(short_code)
        except ValueError as e:
            raise ValidationError(str(e))

        link = await self._uow.links.get_by_short_code(str(code))
        if link is None:
            raise LinkNotFoundError()

        from ...infrastructure.settings import settings

        stats = await self._uow.stats.get_by_link_id(link.id)
        clicks = stats.clicks if stats else 0
        last_used_at = stats.last_used_at if stats else None

        full_short_url = f"{settings.BASE_URL}/{settings.SHORT_LINK_PREFIX}/{link.short_code}"
        is_expired = link.is_expired(datetime.now(timezone.utc))

        return LinkInfoResponse(
            short_code=str(link.short_code),
            original_url=str(link.original_url),
            created_at=link.created_at,
            updated_at=link.updated_at,
            expires_at=link.expires_at.value if link.expires_at else None,
            owner_user_id=link.owner_user_id,
            is_deleted=link.is_deleted,
            full_short_url=full_short_url,
            is_expired=is_expired,
            project_id=link.project_id,
            clicks=clicks,
            last_used_at=last_used_at,
        )