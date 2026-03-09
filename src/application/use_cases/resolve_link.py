from typing import Optional
from uuid import UUID

from ...domain.value_objects.short_code import ShortCode
from ..dto.link_dto import ResolveLinkResponse
from ..errors.errors import LinkNotFoundError, LinkNotAvailableError, ValidationError
from ..services.time_provider import TimeProvider
from ...domain.repositories.unit_of_work import IUnitOfWork


class ResolveLinkUseCase:
    def __init__(self, uow: IUnitOfWork, time_provider: TimeProvider) -> None:
        self._uow = uow
        self._time_provider = time_provider

    async def execute(self, short_code: str) -> ResolveLinkResponse:
        try:
            code = ShortCode.from_string(short_code)
        except ValueError as e:
            raise ValidationError(str(e))

        link = await self._uow.links.get_by_short_code(str(code))
        if link is None:
            raise LinkNotFoundError()

        now = self._time_provider.now()
        if not link.is_available(now):
            raise LinkNotAvailableError()

        await self._uow.stats.increment_click(link.id, now)
        await self._uow.commit()

        return ResolveLinkResponse(
            original_url=str(link.original_url),
            expires_at=link.expires_at.value if link.expires_at else None,
            link_id=link.id,
        )