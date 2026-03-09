from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from ..settings import settings


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
    )


engine = create_engine()


AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)