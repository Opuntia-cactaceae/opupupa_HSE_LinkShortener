from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self, Optional


@dataclass(frozen=True, slots=True)
class ExpiresAt:
    value: Optional[datetime]

    def __post_init__(self) -> None:
        if self.value is not None and self.value.tzinfo is None:
            raise ValueError("ExpiresAt must be timezone-aware")

    def is_expired(self, when: datetime) -> bool:
        if self.value is None:
            return False
        if when.tzinfo is None:
            raise ValueError("Comparison datetime must be timezone-aware")
        return when >= self.value

    def __str__(self) -> str:
        if self.value is None:
            return ""
        return self.value.isoformat()

    @classmethod
    def from_datetime(cls, value: Optional[datetime]) -> Self:
        if value is None:
            return cls(None)
        rounded = value.replace(second=0, microsecond=0)
        return cls(rounded)