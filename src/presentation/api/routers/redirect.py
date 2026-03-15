from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from ...schemas.links import ShortCodeField
from ....application.services.time_provider import SystemTimeProvider
from ....application.use_cases.resolve_link import ResolveLinkUseCase
from ..deps import get_cache, get_settings, get_uow

router = APIRouter()


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: ShortCodeField,
    cache=Depends(get_cache),
    uow=Depends(get_uow),
    settings=Depends(get_settings),
) -> RedirectResponse:
    cached = await cache.get(short_code)
    if cached:
        expires_at_str = cached.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if expires_at <= now:
                cached = None

    time_provider = SystemTimeProvider()
    use_case = ResolveLinkUseCase(uow, time_provider)
    result = await use_case.execute(short_code)

    if not cached:
        await cache.set(
            short_code=short_code,
            original_url=result.original_url,
            expires_at=result.expires_at,
            link_id=result.link_id,
            ttl_sec=settings.DEFAULT_CACHE_TTL_SEC,
        )

    return RedirectResponse(url=result.original_url, status_code=307)
