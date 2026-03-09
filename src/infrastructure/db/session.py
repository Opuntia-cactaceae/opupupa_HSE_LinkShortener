from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .engine import AsyncSessionFactory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()