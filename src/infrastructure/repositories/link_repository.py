from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.link import Link
from ...domain.repositories.link_repository import ILinkRepository
from ..db.mappers import link_to_model, model_to_link
from ..db.models.link import LinkModel
from ..db.models.link_stats import LinkStatsModel


class SqlAlchemyLinkRepository(ILinkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_short_code(self, code: str) -> Optional[Link]:
        stmt = select(LinkModel).where(
            LinkModel.short_code == code,
            LinkModel.is_deleted == False
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_link(model)

    async def get_by_id(self, id: UUID) -> Optional[Link]:
        stmt = select(LinkModel).where(
            LinkModel.id == id,
            LinkModel.is_deleted == False
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_link(model)

    async def find_by_original_url(
        self, url: str, limit: int = 100, offset: int = 0
    ) -> Sequence[Link]:
        stmt = (
            select(LinkModel)
            .where(LinkModel.original_url == url, LinkModel.is_deleted == False)
            .limit(limit)
            .offset(offset)
            .order_by(LinkModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_link(model) for model in models]

    async def exists_short_code(self, code: str) -> bool:
        stmt = select(LinkModel.id).where(
            LinkModel.short_code == code,
            LinkModel.is_deleted == False
        ).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add(self, link: Link) -> None:
        model = link_to_model(link)
        self._session.add(model)

    async def update(self, link: Link) -> None:
        model = link_to_model(link)
        await self._session.merge(model)

    async def list_expired(self, now: datetime, limit: int = 1000) -> Sequence[Link]:
        stmt = (
            select(LinkModel)
            .where(LinkModel.expires_at <= now)
            .where(LinkModel.expired_at.is_(None))
            .where(LinkModel.is_deleted == False)
            .limit(limit)
            .order_by(LinkModel.expires_at.asc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_link(model) for model in models]

    async def list_expired_history(
        self, owner_user_id: Optional[UUID], limit: int = 100, offset: int = 0
    ) -> Sequence[Link]:
        stmt = select(LinkModel).where(
            LinkModel.expired_at.is_not(None),
            LinkModel.is_deleted == False
        )
        if owner_user_id is not None:
            stmt = stmt.where(LinkModel.owner_user_id == owner_user_id)
        stmt = stmt.order_by(LinkModel.expired_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_link(model) for model in models]

    async def find_stale_links(
        self, stale_threshold: datetime, limit: int = 1000
    ) -> Sequence[Link]:
        stmt = (
            select(LinkModel)
            .join(LinkStatsModel, LinkModel.id == LinkStatsModel.link_id)
            .where(
                and_(
                    LinkModel.expired_at.is_(None),
                    LinkModel.is_deleted == False,
                    or_(
                        and_(
                            LinkStatsModel.last_used_at.is_(None),
                            LinkModel.created_at < stale_threshold,
                        ),
                        LinkStatsModel.last_used_at < stale_threshold,
                    ),
                )
            )
            .limit(limit)
            .order_by(LinkModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_link(model) for model in models]

    async def find_by_project_id(
        self, project_id: UUID, limit: int = 100, offset: int = 0
    ) -> Sequence[Link]:
        stmt = (
            select(LinkModel)
            .where(LinkModel.project_id == project_id)
            .where(LinkModel.is_deleted == False)
            .limit(limit)
            .offset(offset)
            .order_by(LinkModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_link(model) for model in models]