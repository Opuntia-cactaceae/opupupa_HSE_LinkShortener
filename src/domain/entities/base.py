from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID, uuid4

T = TypeVar("T", bound=UUID)


class Entity(Generic[T]):
    def __init__(self, id: T, created_at: datetime) -> None:
        self._id = id
        self._created_at = created_at

    @property
    def id(self) -> T:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


class AggregateRoot(Entity[UUID]):
    def __init__(self, id: UUID | None = None, created_at: datetime | None = None) -> None:
        if id is None:
            id = uuid4()
        if created_at is None:
            created_at = datetime.now()
        super().__init__(id, created_at)
