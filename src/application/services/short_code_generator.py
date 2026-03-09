import secrets
import string
from abc import ABC, abstractmethod


class ShortCodeGenerator(ABC):
    @abstractmethod
    def generate(self) -> str:
        raise NotImplementedError


class Base62ShortCodeGenerator(ShortCodeGenerator):
    def __init__(self, length: int = 8) -> None:
        if length < 7 or length > 10:
            raise ValueError("Length must be between 7 and 10")
        self._length = length
        self._chars = string.ascii_letters + string.digits

    def generate(self) -> str:
        return "".join(secrets.choice(self._chars) for _ in range(self._length))