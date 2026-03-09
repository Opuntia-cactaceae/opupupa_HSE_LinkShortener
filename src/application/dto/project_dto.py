from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CreateProjectRequest(BaseModel):
    name: str


class UpdateProjectRequest(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    owner_user_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectLinksRequest(BaseModel):
    page: int = 1
    size: int = 20


class ProjectLinksResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    expired_at: Optional[datetime]
    clicks: int
    last_used_at: Optional[datetime]
    owner_user_id: Optional[UUID]
    project_id: Optional[UUID]