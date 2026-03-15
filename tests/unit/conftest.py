import os
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.infrastructure.settings import Settings


if "ENV_FILE" not in os.environ:
    os.environ.update(
        {
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "REDIS_URL": "redis://localhost:6379/1",
            "JWT_SECRET": "test-secret-key-for-testing-only",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
        }
    )


def pytest_configure():
    pass


@pytest.fixture(scope="session")
def test_settings() -> Settings:

    class TestSettings(Settings):
        model_config = {
            "env_file": None,
            "case_sensitive": False,
        }

    return TestSettings()


@pytest.fixture(scope="session", autouse=True)
def patch_password_hasher():
    from unittest.mock import patch

    def fast_hash(self, password: str) -> str:
        return f"test_hash_{password}"

    def fast_verify(self, password: str, hashed: str) -> bool:
        return hashed == f"test_hash_{password}"

    with patch(
        "src.infrastructure.auth.password_hasher.BcryptPasswordHasher.hash",
        fast_hash,
    ), patch(
        "src.infrastructure.auth.password_hasher.BcryptPasswordHasher.verify",
        fast_verify,
    ):
        yield


@pytest.fixture
def smoke_test_data():
    return {
        "original_url": "https://example.com",
        "short_code": "test123",
    }

@pytest.fixture
def sample_user_id():
    return uuid4()


@pytest.fixture
def sample_project_id():
    return uuid4()


@pytest.fixture
def mock_time_provider():
    provider = Mock()
    provider.now = Mock(return_value=datetime.now(timezone.utc))
    return provider


@pytest.fixture
def sample_email():
    return "test@example.com"


@pytest.fixture
def sample_password():
    return "password123"