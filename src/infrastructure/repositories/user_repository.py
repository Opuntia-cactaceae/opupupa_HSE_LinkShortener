from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.user import User
from ...domain.repositories.user_repository import IUserRepository
from ..db.mappers import model_to_user, user_to_model
from ..db.models.user import UserModel


class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        normalized_email = email.strip().lower()
        stmt = select(UserModel).where(UserModel.email == normalized_email)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_user(model)

    async def get_by_id(self, id: UUID) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.id == id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model_to_user(model)

    async def add(self, user: User) -> None:
        model = user_to_model(user)
        self._session.add(model)