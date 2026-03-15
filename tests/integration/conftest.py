import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    AsyncTransaction,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

#вот этим тестам реально нужен свой енвшник
env_file = os.environ.get("ENV_FILE")
if env_file and os.path.exists(env_file):
    from dotenv import load_dotenv

    load_dotenv(env_file, override=True)


os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRES_MIN", "30")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "INFO")

from src.infrastructure.cache.redis_client import redis_client as global_redis_client
from src.infrastructure.db.models import Base
from src.infrastructure.settings import settings





@pytest_asyncio.fixture(scope="session")
def event_loop():
    
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()






_TABLES_CREATED = False


@pytest.fixture(scope="session")
def engine() -> AsyncGenerator[AsyncEngine, None]:
    
    eng = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        poolclass=NullPool,
    )
    try:
        yield eng
    finally:
        
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(eng.dispose())
            else:
                loop.run_until_complete(eng.dispose())
        except RuntimeError:
            
            pass


@pytest_asyncio.fixture(scope="session")
async def create_tables(engine: AsyncEngine):
    
    global _TABLES_CREATED

    if not _TABLES_CREATED:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
        _TABLES_CREATED = True

    yield


@pytest_asyncio.fixture
async def connection(
    engine: AsyncEngine,
    create_tables,
) -> AsyncGenerator[AsyncConnection, None]:
    
    async with engine.connect() as conn:
        yield conn


@pytest_asyncio.fixture
async def transaction(
    connection: AsyncConnection,
) -> AsyncGenerator[AsyncTransaction, None]:
    
    tx = await connection.begin()
    try:
        yield tx
    finally:
        if tx.is_active:
            await tx.rollback()


@pytest_asyncio.fixture
async def db_session(
    connection: AsyncConnection,
    transaction: AsyncTransaction,
) -> AsyncGenerator[AsyncSession, None]:
    
    session = AsyncSession(bind=connection, expire_on_commit=False)
    sync_session = session.sync_session

    await session.begin_nested()

    @event.listens_for(sync_session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and trans._parent is not None and not trans._parent.nested:
            if connection.in_transaction():
                sess.begin_nested()

    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def patched_session_factory(
    connection: AsyncConnection,
    transaction: AsyncTransaction,
    db_session: AsyncSession,
):
    
    from unittest.mock import patch

    from fastapi import HTTPException

    from src.application.errors.errors import ApplicationError
    from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

    def test_session_factory() -> AsyncSession:
        session = AsyncSession(bind=connection, expire_on_commit=False)
        sync_session = session.sync_session

        sync_session.begin_nested()

        @event.listens_for(sync_session, "after_transaction_end")
        def restart_savepoint(sess, trans):
            if trans.nested and trans._parent is not None and not trans._parent.nested:
                if connection.in_transaction():
                    db_session.expire_all()
                    sess.begin_nested()

        @event.listens_for(sync_session, "after_commit")
        def expire_db_session(_):
            db_session.expire_all()

        return session

    original_aexit = SqlAlchemyUnitOfWork.__aexit__

    async def patched_aexit(self, exc_type, exc_val, exc_tb):
        
        if exc_type is not None and (
                issubclass(exc_type, HTTPException)
                or issubclass(exc_type, ApplicationError)
        ):
            if self._session is not None:
                await self._session.close()
                self._session = None
                self._users = None
                self._links = None
                self._stats = None
                self._projects = None

            db_session.expire_all()
            return

        return await original_aexit(self, exc_type, exc_val, exc_tb)

    with patch(
        "src.infrastructure.db.unit_of_work.AsyncSessionFactory",
        test_session_factory,
    ), patch.object(SqlAlchemyUnitOfWork, "__aexit__", patched_aexit):
        yield





@pytest_asyncio.fixture
async def redis_client():
    
    import redis.asyncio as redis

    client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )

    try:
        await client.ping()
    except Exception as e:
        pytest.skip(f"Redis unavailable: {e}")

    global_redis_client._client = client

    try:
        yield global_redis_client
    finally:
        await client.aclose()


@pytest_asyncio.fixture(autouse=True)
async def clean_redis(redis_client):
    
    await redis_client.client.flushdb()
    try:
        yield
    finally:
        await redis_client.client.flushdb()





@pytest_asyncio.fixture
async def app(create_tables, redis_client, patched_session_factory):
    
    from src.presentation.api.app import create_app

    application = create_app()
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac