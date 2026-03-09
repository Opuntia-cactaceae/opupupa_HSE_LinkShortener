from dataclasses import dataclass
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...infrastructure.auth import BcryptPasswordHasher, JwtTokenProvider
from ...infrastructure.cache import LinkCache
from ...infrastructure.db import SqlAlchemyUnitOfWork
from ...infrastructure.settings import settings

security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: UUID


async def get_uow() -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    uow = SqlAlchemyUnitOfWork()
    async with uow:
        yield uow


def get_cache() -> LinkCache:
    return LinkCache()


def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


def get_token_provider() -> JwtTokenProvider:
    return JwtTokenProvider()


def get_settings():
    return settings


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token_provider: JwtTokenProvider = Depends(get_token_provider),
) -> Optional[str]:
    if credentials is None:
        return None

    user_id = token_provider.decode(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return str(user_id)


async def get_current_user(
    user_id: Optional[str] = Depends(get_current_user_id),
) -> CurrentUser:
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return CurrentUser(id=UUID(user_id))