from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID


class TokenProvider(ABC):
    @abstractmethod
    def encode(self, user_id: UUID) -> str:
        raise NotImplementedError

    @abstractmethod
    def decode(self, token: str) -> Optional[UUID]:
        raise NotImplementedError