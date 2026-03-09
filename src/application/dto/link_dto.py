from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class ShortenLinkRequest:
    original_url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    project_id: Optional[UUID] = None


@dataclass
class ShortenLinkResponse:
    short_code: str
    original_url: str
    expires_at: Optional[datetime]
    created_at: datetime
    link_id: UUID
    full_short_url: str
    is_expired: bool
    project_id: Optional[UUID]
    owner_user_id: Optional[UUID]
    clicks: int = 0


@dataclass
class UpdateLinkRequest:
    original_url: Optional[str] = None
    short_code: Optional[str] = None
    expires_at: Optional[datetime] = None
    project_id: Optional[UUID] = None


@dataclass
class LinkInfoResponse:
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


@dataclass
class LinkStatsResponse:
    short_code: str
    full_short_url: str
    clicks: int
    last_used_at: Optional[datetime]


@dataclass
class SearchLinksQuery:
    original_url: str
    limit: int = 100
    offset: int = 0


@dataclass
class ResolveLinkResponse:
    original_url: str
    expires_at: Optional[datetime]
    link_id: UUID


@dataclass
class ExpiredLinksResponse:
    short_code: str
    original_url: str
    created_at: datetime
    expired_at: datetime
    clicks: int
    last_used_at: Optional[datetime]
    owner_user_id: Optional[UUID]
    project_id: Optional[UUID]


@dataclass
class ProjectLinkResponse:
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    expired_at: Optional[datetime]
    clicks: int
    last_used_at: Optional[datetime]
    owner_user_id: Optional[UUID]
    project_id: Optional[UUID]