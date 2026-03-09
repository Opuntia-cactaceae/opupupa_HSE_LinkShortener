from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from ..entities.user import User


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, user: User) -> None:
        raise NotImplementedError
