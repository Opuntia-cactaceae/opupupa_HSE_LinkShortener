from abc import ABC, abstractmethod
from typing import Optional, Sequence
from uuid import UUID

from ..entities.project import Project


class IProjectRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Project]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_name_and_owner(self, name: str, owner_user_id: UUID) -> Optional[Project]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_owner(self, owner_user_id: UUID, limit: int = 100, offset: int = 0) -> Sequence[Project]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, project: Project) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, project: Project) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, project: Project) -> None:
        raise NotImplementedError
