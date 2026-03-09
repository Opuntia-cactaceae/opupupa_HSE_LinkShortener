import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


_SHORT_CODE_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def _normalize_expires_at(v: Optional[datetime]) -> Optional[datetime]:
    if v is None:
        return None

    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    else:
        v = v.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    if v <= now:
        raise ValueError("must be in the future")
    if v.second != 0 or v.microsecond != 0:
        raise ValueError("must be rounded to minute precision")

    return v


class ShortCodeField(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        return core_schema.no_info_after_validator_function(
            cls.validate,
            handler(str),
        )

    @classmethod
    def validate(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("must be a string")

        v = v.strip()

        if len(v) < 3 or len(v) > 32:
            raise ValueError("must be between 3 and 32 characters")

        if not _SHORT_CODE_PATTERN.fullmatch(v):
            raise ValueError(
                "can only contain letters, numbers, hyphens and underscores"
            )

        return v


class ShortenLinkRequest(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[ShortCodeField] = None
    expires_at: Optional[datetime] = None
    project_id: Optional[UUID] = None

    model_config = {
        "extra": "forbid",
    }

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _normalize_expires_at(v)


class ShortenLinkResponse(BaseModel):
    short_code: str
    full_short_url: str
    original_url: str
    expires_at: Optional[datetime]
    created_at: datetime
    link_id: UUID
    is_expired: bool
    project_id: Optional[UUID]
    owner_user_id: Optional[UUID]
    clicks: int = 0

    @classmethod
    def from_dto(cls, dto):
        return cls(
            short_code=dto.short_code,
            full_short_url=dto.full_short_url,
            original_url=dto.original_url,
            expires_at=dto.expires_at,
            created_at=dto.created_at,
            link_id=dto.link_id,
            is_expired=dto.is_expired,
            project_id=dto.project_id,
            owner_user_id=dto.owner_user_id,
            clicks=dto.clicks,
        )


class UpdateLinkRequest(BaseModel):
    original_url: Optional[HttpUrl] = None
    new_short_code: Optional[ShortCodeField] = None
    expires_at: Optional[datetime] = None
    project_id: Optional[UUID] = None

    model_config = {
        "extra": "forbid",
    }

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _normalize_expires_at(v)


class LinkInfoResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    owner_user_id: Optional[UUID]
    is_deleted: bool
    full_short_url: str
    is_expired: bool
    project_id: Optional[UUID]
    clicks: int = 0
    last_used_at: Optional[datetime] = None

    @classmethod
    def from_dto(cls, dto):
        return cls(
            short_code=dto.short_code,
            original_url=dto.original_url,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            expires_at=dto.expires_at,
            owner_user_id=dto.owner_user_id,
            is_deleted=dto.is_deleted,
            full_short_url=dto.full_short_url,
            is_expired=dto.is_expired,
            project_id=dto.project_id,
            clicks=dto.clicks,
            last_used_at=dto.last_used_at,
        )


class LinkStatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    clicks: int
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    full_short_url: str
    is_expired: bool
    project_id: Optional[UUID]
    owner_user_id: Optional[UUID]

    @classmethod
    def from_dto(cls, dto):
        return cls(
            short_code=dto.short_code,
            original_url=dto.original_url,
            created_at=dto.created_at,
            clicks=dto.clicks,
            last_used_at=dto.last_used_at,
            expires_at=dto.expires_at,
            full_short_url=dto.full_short_url,
            is_expired=dto.is_expired,
            project_id=dto.project_id,
            owner_user_id=dto.owner_user_id,
        )


class ExpiredLinksQuery(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

    model_config = {
        "extra": "forbid",
    }


class ExpiredLinksResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expired_at: datetime
    clicks: int
    last_used_at: Optional[datetime]
    owner_user_id: Optional[UUID]
    project_id: Optional[UUID]

    @classmethod
    def from_dto(cls, dto):
        return cls(
            short_code=dto.short_code,
            original_url=dto.original_url,
            created_at=dto.created_at,
            expired_at=dto.expired_at,
            clicks=dto.clicks,
            last_used_at=dto.last_used_at,
            owner_user_id=dto.owner_user_id,
            project_id=dto.project_id,
        )


class SearchLinksQuery(BaseModel):
    original_url: HttpUrl
    page: int = Field(1, ge=1)
    size: int = Field(100, ge=1, le=100)

    model_config = {
        "extra": "forbid",
    }


class SearchLinksResponse(BaseModel):
    items: list[LinkInfoResponse]
    page: int
    size: int
    total: Optional[int] = None