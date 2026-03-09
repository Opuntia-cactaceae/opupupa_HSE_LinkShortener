from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.repositories.unit_of_work import IUnitOfWork
from ..repositories import (
    SqlAlchemyLinkRepository,
    SqlAlchemyLinkStatsRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyUserRepository,
)
from .engine import AsyncSessionFactory


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self._session: Optional[AsyncSession] = None
        self._users: Optional[SqlAlchemyUserRepository] = None
        self._links: Optional[SqlAlchemyLinkRepository] = None
        self._stats: Optional[SqlAlchemyLinkStatsRepository] = None
        self._projects: Optional[SqlAlchemyProjectRepository] = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = AsyncSessionFactory()
        self._users = SqlAlchemyUserRepository(self._session)
        self._links = SqlAlchemyLinkRepository(self._session)
        self._stats = SqlAlchemyLinkStatsRepository(self._session)
        self._projects = SqlAlchemyProjectRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
        if self._session is not None:
            await self._session.close()
            self._session = None
            self._users = None
            self._links = None
            self._stats = None
            self._projects = None

    @property
    def users(self) -> SqlAlchemyUserRepository:
        if self._users is None:
            raise RuntimeError("UnitOfWork not started")
        return self._users

    @property
    def links(self) -> SqlAlchemyLinkRepository:
        if self._links is None:
            raise RuntimeError("UnitOfWork not started")
        return self._links

    @property
    def stats(self) -> SqlAlchemyLinkStatsRepository:
        if self._stats is None:
            raise RuntimeError("UnitOfWork not started")
        return self._stats

    @property
    def projects(self) -> SqlAlchemyProjectRepository:
        if self._projects is None:
            raise RuntimeError("UnitOfWork not started")
        return self._projects

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork not started")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork not started")
        await self._session.rollback()