from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, password: str, hashed_password: str) -> bool:
        raise NotImplementedError