from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from ...domain.value_objects.expires_at import ExpiresAt
from ...domain.value_objects.original_url import OriginalUrl
from ...domain.value_objects.short_code import ShortCode
from ..dto.link_dto import UpdateLinkRequest
from ..errors.errors import (
    LinkNotFoundError,
    ShortCodeAlreadyExistsError,
    UserNotAuthorizedError,
    ValidationError,
)
from ...domain.repositories.unit_of_work import IUnitOfWork


class UpdateLinkUseCase:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, short_code: str, request: UpdateLinkRequest, actor_user_id: Optional[UUID]
    ) -> None:
        try:
            code = ShortCode.from_string(short_code)
        except ValueError as e:
            raise ValidationError(str(e))

        link = await self._uow.links.get_by_short_code(str(code))
        if link is None:
            raise LinkNotFoundError()

        if actor_user_id is None:
            raise UserNotAuthorizedError()

        if not link.is_owner(actor_user_id):
            raise UserNotAuthorizedError()

        if request.original_url is not None:
            try:
                new_url = OriginalUrl.from_string(request.original_url)
            except ValueError as e:
                raise ValidationError(str(e))
            link.update_original_url(new_url)

        if request.short_code is not None:
            try:
                new_short_code = ShortCode.from_string(request.short_code)
            except ValueError as e:
                raise ValidationError(str(e))
            link.update_short_code(new_short_code)

        if request.expires_at is not None:
            try:
                new_expires_at = ExpiresAt.from_datetime(request.expires_at)
            except ValueError as e:
                raise ValidationError(str(e))
            link.update_expires_at(new_expires_at)
        elif request.expires_at is None and link.expires_at is not None:
            link.update_expires_at(None)

        if request.project_id is not None:
            project = await self._uow.projects.get_by_id(request.project_id)
            if project is None:
                raise ValidationError("Project not found")
            if not project.is_owner(actor_user_id):
                raise ValidationError("Project does not belong to user")
            link.update_project_id(request.project_id)
        elif request.project_id is None and link.project_id is not None:
            link.update_project_id(None)

        await self._uow.links.update(link)
        try:
            await self._uow.commit()
        except IntegrityError:
            raise ShortCodeAlreadyExistsError()