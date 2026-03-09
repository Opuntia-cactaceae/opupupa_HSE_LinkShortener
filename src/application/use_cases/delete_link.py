from typing import Optional
from uuid import UUID

from ...domain.value_objects.short_code import ShortCode
from ..errors.errors import LinkNotFoundError, UserNotAuthorizedError, ValidationError
from ...domain.repositories.unit_of_work import IUnitOfWork


class DeleteLinkUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, short_code: str, actor_user_id: Optional[UUID]
    ) -> None:
        try:
            code = ShortCode.from_string(short_code)
        except ValueError as e:
            raise ValidationError(str(e))

        link = await self._uow.links.get_by_short_code(str(code))
        if link is None:
            raise LinkNotFoundError()

        if not link.is_owner(actor_user_id):
            raise UserNotAuthorizedError()

        link.delete()
        await self._uow.links.update(link)
        await self._uow.commit()