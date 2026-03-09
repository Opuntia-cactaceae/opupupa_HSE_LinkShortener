from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar
from uuid import UUID

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[T]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, entity: T) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity: T) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity: T) -> None:
        raise NotImplementedError
