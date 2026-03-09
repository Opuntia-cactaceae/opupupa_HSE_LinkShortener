from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ...schemas.links import (
    LinkInfoResponse,
    LinkStatsResponse,
    SearchLinksQuery,
    SearchLinksResponse,
    ShortenLinkRequest,
    ShortenLinkResponse,
    UpdateLinkRequest,
    ShortCodeField,
    ExpiredLinksQuery,
    ExpiredLinksResponse,
)
from ....application.dto.link_dto import (
    ShortenLinkRequest as ShortenLinkRequestDto,
    UpdateLinkRequest as UpdateLinkRequestDto,
    SearchLinksQuery as SearchLinksQueryDto,
)
from ....application.services.short_code_generator import Base62ShortCodeGenerator
from ....application.services.time_provider import SystemTimeProvider
from ....application.use_cases.delete_link import DeleteLinkUseCase
from ....application.use_cases.get_link_info import GetLinkInfoUseCase
from ....application.use_cases.get_link_stats import GetLinkStatsUseCase
from ....application.use_cases.search_link_by_original_url import SearchLinkByOriginalUrlUseCase
from ....application.use_cases.shorten_link import ShortenLinkUseCase
from ....application.use_cases.update_link import UpdateLinkUseCase
from ....application.use_cases.list_expired_links import ListExpiredLinksUseCase
from ..deps import (
    get_cache,
    get_current_user_id,
    get_settings,
    get_uow,
)

router = APIRouter()


@router.post(
    "/shorten",
    response_model=ShortenLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def shorten(
    request: ShortenLinkRequest,
    uow=Depends(get_uow),
    cache=Depends(get_cache),
    settings=Depends(get_settings),
    actor_user_id: Optional[str] = Depends(get_current_user_id),
) -> ShortenLinkResponse:
    dto_request = ShortenLinkRequestDto(
        original_url=str(request.original_url),
        custom_alias=request.custom_alias,
        expires_at=request.expires_at,
        project_id=request.project_id,
    )
    use_case = ShortenLinkUseCase(
        uow,
        Base62ShortCodeGenerator(),
        SystemTimeProvider(),
    )
    user_uuid = UUID(actor_user_id) if actor_user_id else None
    dto_response = await use_case.execute(
        dto_request,
        user_uuid,
    )
    await cache.set(
        short_code=dto_response.short_code,
        original_url=dto_response.original_url,
        expires_at=dto_response.expires_at,
        link_id=dto_response.link_id,
        ttl_sec=settings.DEFAULT_CACHE_TTL_SEC,
    )
    return ShortenLinkResponse.from_dto(dto_response)


@router.get("/search", response_model=SearchLinksResponse)
async def search_links(
    query: SearchLinksQuery = Depends(),
    uow=Depends(get_uow),
) -> SearchLinksResponse:
    offset = (query.page - 1) * query.size
    limit = query.size
    dto_query = SearchLinksQueryDto(
        original_url=str(query.original_url),
        limit=limit,
        offset=offset,
    )
    use_case = SearchLinkByOriginalUrlUseCase(uow)
    items = await use_case.execute(dto_query)
    return SearchLinksResponse(
        items=[LinkInfoResponse.from_dto(item) for item in items],
        page=query.page,
        size=query.size,
    )


@router.get("/expired", response_model=list[ExpiredLinksResponse])
async def list_expired_links(
    query: ExpiredLinksQuery = Depends(),
    uow=Depends(get_uow),
    actor_user_id: Optional[str] = Depends(get_current_user_id),
) -> list[ExpiredLinksResponse]:
    user_uuid = UUID(actor_user_id) if actor_user_id else None
    use_case = ListExpiredLinksUseCase(uow)
    items = await use_case.execute(user_uuid, query.page, query.size)
    return [ExpiredLinksResponse.from_dto(item) for item in items]


@router.get("/{short_code}", response_model=LinkInfoResponse)
async def get_link_info(
    short_code: ShortCodeField,
    uow=Depends(get_uow),
) -> LinkInfoResponse:
    use_case = GetLinkInfoUseCase(uow)
    dto = await use_case.execute(short_code)
    return LinkInfoResponse.from_dto(dto)


@router.put("/{short_code}", response_model=LinkInfoResponse)
async def update_link(
    short_code: ShortCodeField,
    request: UpdateLinkRequest,
    uow=Depends(get_uow),
    cache=Depends(get_cache),
    actor_user_id: Optional[str] = Depends(get_current_user_id),
) -> LinkInfoResponse:
    dto_request = UpdateLinkRequestDto(
        original_url=str(request.original_url) if request.original_url is not None else None,
        short_code=request.new_short_code,
        expires_at=request.expires_at,
        project_id=request.project_id,
    )
    user_uuid = UUID(actor_user_id) if actor_user_id else None
    use_case = UpdateLinkUseCase(uow)
    await use_case.execute(short_code, dto_request, user_uuid)
    await cache.invalidate(short_code)
    if request.new_short_code:
        await cache.invalidate(request.new_short_code)

    info_use_case = GetLinkInfoUseCase(uow)
    dto = await info_use_case.execute(request.new_short_code or short_code)
    return LinkInfoResponse.from_dto(dto)


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    short_code: ShortCodeField,
    uow=Depends(get_uow),
    cache=Depends(get_cache),
    actor_user_id: Optional[str] = Depends(get_current_user_id),
) -> None:
    user_uuid = UUID(actor_user_id) if actor_user_id else None
    use_case = DeleteLinkUseCase(uow)
    await use_case.execute(short_code, user_uuid)
    await cache.invalidate(short_code)


@router.get("/{short_code}/stats", response_model=LinkStatsResponse)
async def get_link_stats(
    short_code: ShortCodeField,
    uow=Depends(get_uow),
) -> LinkStatsResponse:
    use_case = GetLinkStatsUseCase(uow)
    dto = await use_case.execute(short_code)
    return LinkStatsResponse.from_dto(dto)