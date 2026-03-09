from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.link_stats import LinkStats
from ...domain.repositories.link_stats_repository import ILinkStatsRepository
from ..db.mappers import link_stats_to_model, model_to_link_stats
from ..db.models.link_stats import LinkStatsModel


class SqlAlchemyLinkStatsRepository(ILinkStatsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_link_id(self, link_id: UUID) -> Optional[LinkStats]:
        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id == link_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_link_stats(model)

    async def get_by_link_ids(self, link_ids: Sequence[UUID]) -> Sequence[LinkStats]:
        if not link_ids:
            return []
        stmt = select(LinkStatsModel).where(LinkStatsModel.link_id.in_(link_ids))
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model_to_link_stats(model) for model in models]

    async def add(self, stats: LinkStats) -> None:
        model = link_stats_to_model(stats)
        self._session.add(model)

    async def increment_click(self, link_id: UUID, used_at: datetime) -> None:
        stmt = (
            update(LinkStatsModel)
            .where(LinkStatsModel.link_id == link_id)
            .values(
                clicks=LinkStatsModel.clicks + 1,
                last_used_at=used_at,
            )
        )
        await self._session.execute(stmt)