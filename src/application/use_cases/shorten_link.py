from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from ...domain.entities.link import Link
from ...domain.entities.link_stats import LinkStats
from ...domain.value_objects.expires_at import ExpiresAt
from ...domain.value_objects.original_url import OriginalUrl
from ...domain.value_objects.short_code import ShortCode
from ..dto.link_dto import ShortenLinkRequest, ShortenLinkResponse
from ..errors.errors import ShortCodeAlreadyExistsError, ValidationError
from ..services.short_code_generator import ShortCodeGenerator
from ..services.time_provider import TimeProvider
from ...domain.repositories.unit_of_work import IUnitOfWork


class ShortenLinkUseCase:
    """Выполняет создание короткой ссылки на основании исходного URL и параметров запроса."""
    def __init__(
        self,
        uow: IUnitOfWork,
        short_code_generator: ShortCodeGenerator,
        time_provider: TimeProvider,
    ) -> None:
        self._uow = uow
        self._short_code_generator = short_code_generator
        self._time_provider = time_provider

    async def execute(
        self, request: ShortenLinkRequest, actor_user_id: Optional[UUID] = None
    ) -> ShortenLinkResponse:
        """Обрабатывает запрос на создание короткой ссылки.

        Проверяет входные данные, генерирует короткий код и сохраняет новую сущность ссылки.
        """
        try:
            original_url = OriginalUrl.from_string(request.original_url)
        except ValueError as e:
            raise ValidationError(str(e))

        expires_at = None
        if request.expires_at is not None:
            try:
                expires_at = ExpiresAt.from_datetime(request.expires_at)
            except ValueError as e:
                raise ValidationError(str(e))

        project_id = request.project_id
        if project_id is not None:
            if actor_user_id is None:
                raise ValidationError("Anonymous users cannot assign projects")
            project = await self._uow.projects.get_by_id(project_id)
            if project is None:
                raise ValidationError("Project not found")
            if not project.is_owner(actor_user_id):
                raise ValidationError("Project does not belong to user")

        short_code_value = request.custom_alias
        if short_code_value is None:
            return await self._create_with_generated_code(original_url, expires_at, actor_user_id, project_id)
        else:
            try:
                short_code = ShortCode.from_string(short_code_value)
            except ValueError as e:
                raise ValidationError(str(e))
            return await self._create_with_specific_code(short_code, original_url, expires_at, actor_user_id, project_id)

    async def _create_with_generated_code(
        self,
        original_url: OriginalUrl,
        expires_at: Optional[ExpiresAt],
        actor_user_id: Optional[UUID],
        project_id: Optional[UUID],
    ) -> ShortenLinkResponse:
        for attempt in range(10):
            code = self._short_code_generator.generate()
            short_code = ShortCode.from_string(code)
            try:
                return await self._attempt_create_link(short_code, original_url, expires_at, actor_user_id, project_id)
            except ShortCodeAlreadyExistsError:
                if attempt == 9:
                    raise ShortCodeAlreadyExistsError("Could not generate unique short code")
                continue

        raise ShortCodeAlreadyExistsError("Could not generate unique short code")

    async def _create_with_specific_code(
        self,
        short_code: ShortCode,
        original_url: OriginalUrl,
        expires_at: Optional[ExpiresAt],
        actor_user_id: Optional[UUID],
        project_id: Optional[UUID],
    ) -> ShortenLinkResponse:
        try:
            return await self._attempt_create_link(short_code, original_url, expires_at, actor_user_id, project_id)
        except ShortCodeAlreadyExistsError:
            raise ShortCodeAlreadyExistsError()

    async def _attempt_create_link(
        self,
        short_code: ShortCode,
        original_url: OriginalUrl,
        expires_at: Optional[ExpiresAt],
        actor_user_id: Optional[UUID],
        project_id: Optional[UUID],
    ) -> ShortenLinkResponse:
        link = Link.create(
            short_code=short_code,
            original_url=original_url,
            owner_user_id=actor_user_id,
            expires_at=expires_at,
            project_id=project_id,
        )

        stats = LinkStats.create(link.id)

        await self._uow.links.add(link)
        await self._uow.stats.add(stats)
        try:
            await self._uow.commit()
        except IntegrityError:
            raise ShortCodeAlreadyExistsError()

        from ...infrastructure.settings import settings
        full_short_url = f"{settings.BASE_URL}/{settings.SHORT_LINK_PREFIX}/{short_code}"
        return ShortenLinkResponse(
            short_code=str(short_code),
            original_url=str(original_url),
            expires_at=expires_at.value if expires_at else None,
            created_at=link.created_at,
            link_id=link.id,
            full_short_url=full_short_url,
            is_expired=False,
            project_id=project_id,
            owner_user_id=actor_user_id,
            clicks=0,
        )