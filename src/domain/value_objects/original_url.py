import re
from dataclasses import dataclass
from typing import Self
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class OriginalUrl:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("URL cannot be empty")

        parsed = urlparse(self.value)
        if not parsed.scheme:
            raise ValueError("URL must have a scheme (http or https)")
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL scheme must be http or https")
        if not parsed.netloc:
            raise ValueError("URL must have a hostname")

        if len(self.value) > 2000:
            raise ValueError("URL is too long")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> Self:
        return cls(value.strip())
