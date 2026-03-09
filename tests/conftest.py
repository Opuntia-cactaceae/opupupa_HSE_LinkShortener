import asyncio
import os
# Set environment variables before any imports that depend on settings
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "POSTGRES_DSN": "sqlite+aiosqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379/1",  # Use DB index 1 for tests
    "JWT_SECRET": "test-secret-key-for-testing-only",
    "DEBUG": "true",
    "LOG_LEVEL": "DEBUG",
})

from typing import AsyncGenerator, Generator
from unittest.mock import Mock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.settings import Settings
from src.infrastructure.cache.redis_client import RedisClient
from src.infrastructure.db.engine import AsyncSessionFactory, engine
from src.infrastructure.db.models import Base
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from src.presentation.api.app import create_app


def pytest_configure():
    """Additional test configuration."""
    pass


# @pytest.fixture(scope="session")
# def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
#     """Create an event loop for the test session."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Return test settings."""
    # Create a Settings subclass that doesn't load .env file
    class TestSettings(Settings):
        model_config = {
            "env_file": None,
            "case_sensitive": False,
        }
    return TestSettings()


@pytest.fixture(scope="session", autouse=True)
def patch_password_hasher():
    """Patch bcrypt password hasher to use pbkdf2_sha256 for tests."""
    from unittest.mock import patch
    from passlib.context import CryptContext
    test_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    def fast_hash(password: str) -> str:
        return test_context.hash(password)

    def fast_verify(password: str, hashed: str) -> bool:
        return test_context.verify(password, hashed)

    with patch("src.infrastructure.auth.password_hasher.BcryptPasswordHasher.hash", fast_hash), \
         patch("src.infrastructure.auth.password_hasher.BcryptPasswordHasher.verify", fast_verify):
        yield


@pytest.fixture(scope="session")
def db_engine(test_settings: Settings) -> AsyncEngine:
    """Create database engine for tests."""
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=test_settings.DEBUG,
        future=True,
        connect_args={"check_same_thread": False} if "sqlite" in test_settings.DATABASE_URL else {},
    )
    yield engine
    engine.sync_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def init_database(db_engine: AsyncEngine):
    """Create database tables."""
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="session")
async def db_session_factory(db_engine: AsyncEngine):
    """Create async session factory."""
    return async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(db_session_factory, init_database) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session with automatic rollback."""
    async with db_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def patched_session_factory(db_session_factory):
    """Patch AsyncSessionFactory in unit_of_work module."""
    from unittest.mock import patch
    with patch('src.infrastructure.db.unit_of_work.AsyncSessionFactory', db_session_factory):
        yield


@pytest_asyncio.fixture
async def uow(patched_session_factory) -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    """Provide a unit of work using patched session factory."""
    uow_instance = SqlAlchemyUnitOfWork()
    async with uow_instance:
        yield uow_instance


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[RedisClient, None]:
    """Provide a mocked Redis client."""
    from unittest.mock import AsyncMock, MagicMock
    mock_client = AsyncMock()
    mock_client.flushdb = AsyncMock()
    mock_client.set = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    # Pipeline mock for rate limiting
    from unittest.mock import Mock
    mock_pipeline = Mock()
    mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
    mock_pipeline.zcard = Mock(return_value=mock_pipeline)
    mock_pipeline.zadd = Mock(return_value=mock_pipeline)
    mock_pipeline.expire = Mock(return_value=mock_pipeline)
    mock_pipeline.execute = AsyncMock(return_value=[0, 0, 0, 0])  # zremrangebyscore, zcard, zadd, expire results
    mock_client.pipeline = Mock(return_value=mock_pipeline)
    mock_redis_client = MagicMock(spec=RedisClient)
    mock_redis_client.client = mock_client
    mock_redis_client.connect = AsyncMock()
    mock_redis_client.disconnect = AsyncMock()
    yield mock_redis_client


@pytest_asyncio.fixture
async def app(test_settings: Settings, patched_session_factory, redis_client, init_database):
    """Create FastAPI app with test dependencies."""
    # Override settings in the app module
    from src.infrastructure import settings
    original_settings = settings.settings
    # Store original values and override with test settings
    original_values = {}
    for field_name in test_settings.__class__.model_fields:
        original_values[field_name] = getattr(settings.settings, field_name)
        setattr(settings.settings, field_name, getattr(test_settings, field_name))

    # Mock Redis connection, engine disposal, and background jobs to avoid external dependencies
    from unittest.mock import patch, AsyncMock
    from src.infrastructure.cache.redis_client import redis_client as global_redis_client
    from src.infrastructure.jobs.purge_expired_links_job import PurgeExpiredLinksJob
    from src.presentation.api.middleware.rate_limit import RateLimitMiddleware as OriginalRateLimitMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware

    # Create a dummy middleware class that bypasses rate limiting
    class DummyRateLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            print('DummyRateLimitMiddleware.dispatch called')
            return await call_next(request)

    with patch.object(global_redis_client, 'connect', new_callable=AsyncMock) as mock_connect, \
         patch.object(global_redis_client, 'disconnect', new_callable=AsyncMock) as mock_disconnect, \
         patch.object(global_redis_client, '_client', new=redis_client.client), \
         patch.object(PurgeExpiredLinksJob, 'start', new_callable=AsyncMock) as mock_start, \
         patch.object(PurgeExpiredLinksJob, 'stop', new_callable=AsyncMock) as mock_stop, \
         patch('src.presentation.api.app.RateLimitMiddleware', DummyRateLimitMiddleware):
        # No need for dispatch patch since we replaced the whole middleware
        pass
        # Create app
        app = create_app()

        # Override dependencies to use test fixtures
        from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
        from src.infrastructure.cache.link_cache import LinkCache
        from src.presentation.api.deps import get_uow, get_cache

        async def override_get_uow():
            uow_instance = SqlAlchemyUnitOfWork()
            async with uow_instance:
                yield uow_instance

        async def override_get_cache():
            cache = LinkCache()
            # Use test redis client (already patched via global redis_client._client)
            # cache._redis = redis_client.client  # This line causes incorrect nesting
            yield cache

        app.dependency_overrides[get_uow] = override_get_uow
        app.dependency_overrides[get_cache] = override_get_cache

        yield app

        # Clean up overrides
        app.dependency_overrides.clear()

    # Restore original settings values
    for field_name, original_value in original_values.items():
        setattr(settings.settings, field_name, original_value)


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create httpx AsyncClient for testing API endpoints."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# Minimal smoke test helpers
@pytest.fixture
def smoke_test_data():
    """Provide minimal test data for smoke tests."""
    return {
        "original_url": "https://example.com",
        "short_code": "test123",
    }