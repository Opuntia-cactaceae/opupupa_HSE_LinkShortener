import re
from dataclasses import dataclass
from typing import Self

_SHORT_CODE_PATTERN = re.compile(r"[A-Za-z0-9_-]+")

@dataclass(frozen=True, slots=True)
class ShortCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Short code cannot be empty")
        if len(self.value) < 3:
            raise ValueError("Short code must be at least 3 characters")
        if len(self.value) > 32:
            raise ValueError("Short code cannot exceed 32 characters")
        if not _SHORT_CODE_PATTERN.fullmatch(self.value):
            raise ValueError(
                "Short code can only contain letters, numbers, hyphens and underscores"
            )

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> Self:
        return cls(value.strip())