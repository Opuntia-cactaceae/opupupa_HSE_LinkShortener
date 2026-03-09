from abc import ABC, abstractmethod

from .link_repository import ILinkRepository
from .link_stats_repository import ILinkStatsRepository
from .project_repository import IProjectRepository
from .user_repository import IUserRepository


class IUnitOfWork(ABC):
    @property
    @abstractmethod
    def users(self) -> IUserRepository:
        raise NotImplementedError

    @property
    @abstractmethod
    def links(self) -> ILinkRepository:
        raise NotImplementedError

    @property
    @abstractmethod
    def stats(self) -> ILinkStatsRepository:
        raise NotImplementedError

    @property
    @abstractmethod
    def projects(self) -> IProjectRepository:
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError
