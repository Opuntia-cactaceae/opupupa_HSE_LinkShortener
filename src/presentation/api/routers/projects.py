from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...schemas.project import (
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectResponse,
    ProjectLinksQuery,
    ProjectLinksResponse,
)
from ....application.use_cases.create_project import CreateProjectUseCase
from ....application.use_cases.get_project import GetProjectUseCase
from ....application.use_cases.list_projects import ListProjectsUseCase
from ....application.use_cases.update_project import UpdateProjectUseCase
from ....application.use_cases.delete_project import DeleteProjectUseCase
from ....application.use_cases.list_project_links import ListProjectLinksUseCase
from ..deps import get_current_user, get_uow

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    current_user=Depends(get_current_user),
    uow=Depends(get_uow),
):
    use_case = CreateProjectUseCase(uow)
    return await use_case.execute(request, current_user.id)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    current_user=Depends(get_current_user),
    uow=Depends(get_uow),
):
    use_case = ListProjectsUseCase(uow)
    return await use_case.execute(current_user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user=Depends(get_current_user),
    uow=Depends(get_uow),
):
    use_case = GetProjectUseCase(uow)
    return await use_case.execute(project_id, current_user.id)


@router.put("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_project(
    project_id: UUID,
    request: UpdateProjectRequest,
    current_user=Depends(get_current_user),
    uow=Depends(get_uow),
):
    use_case = UpdateProjectUseCase(uow)
    await use_case.execute(project_id, request, current_user.id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user=Depends(get_current_user),
    uow=Depends(get_uow),
):
    use_case = DeleteProjectUseCase(uow)
    await use_case.execute(project_id, current_user.id)


@router.get("/{project_id}/links", response_model=list[ProjectLinksResponse])
async def list_project_links(
    project_id: UUID,
    query: ProjectLinksQuery = Depends(),
    current_user=Depends(get_current_user),
    uow=Depends(get_uow),
):
    use_case = ListProjectLinksUseCase(uow)
    items = await use_case.execute(project_id, current_user.id, query.page, query.size)
    return [
        ProjectLinksResponse(
            short_code=item.short_code,
            original_url=item.original_url,
            created_at=item.created_at,
            expires_at=item.expires_at,
            expired_at=item.expired_at,
            clicks=item.clicks,
            last_used_at=item.last_used_at,
            owner_user_id=item.owner_user_id,
            project_id=item.project_id,
        )
        for item in items
    ]