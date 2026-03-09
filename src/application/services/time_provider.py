from abc import ABC, abstractmethod
from datetime import datetime, timezone


class TimeProvider(ABC):
    @abstractmethod
    def now(self) -> datetime:
        raise NotImplementedError


class SystemTimeProvider(TimeProvider):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)