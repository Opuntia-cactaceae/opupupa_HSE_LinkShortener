from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    model_config = {
        "extra": "forbid",
    }


class UpdateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    model_config = {
        "extra": "forbid",
    }


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    owner_user_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectLinksQuery(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


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