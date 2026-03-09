from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.project import Project
from ...domain.repositories.project_repository import IProjectRepository
from ..db.mappers import model_to_project, project_to_model
from ..db.models.project import ProjectModel


class SqlAlchemyProjectRepository(IProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_project(model)

    async def get_by_name_and_owner(
        self,
        name: str,
        owner_user_id: UUID,
    ) -> Optional[Project]:
        stmt = select(ProjectModel).where(
            ProjectModel.name == name,
            ProjectModel.owner_user_id == owner_user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_project(model)

    async def list_by_owner(
        self,
        owner_user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Project]:
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.owner_user_id == owner_user_id)
            .order_by(ProjectModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_project(model) for model in models]

    async def add(self, project: Project) -> None:
        model = project_to_model(project)
        self._session.add(model)

    async def update(self, project: Project) -> None:
        model = project_to_model(project)
        await self._session.merge(model)

    async def delete(self, project: Project) -> None:
        model = project_to_model(project)
        model = await self._session.merge(model)
        await self._session.delete(model)