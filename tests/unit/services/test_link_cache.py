import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.infrastructure.cache.link_cache import LinkCache


class TestLinkCache:
    """Unit tests for LinkCache class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        # Mock the raw Redis client (async)
        raw_client = AsyncMock()
        raw_client.get = AsyncMock(return_value=None)
        raw_client.setex = AsyncMock()
        raw_client.delete = AsyncMock()

        # Mock the RedisClient wrapper that has .client property
        redis_client_wrapper = AsyncMock()
        redis_client_wrapper.client = raw_client
        return redis_client_wrapper

    @pytest.fixture
    def cache(self, mock_redis_client):
        """Create LinkCache with mocked Redis client."""
        cache = LinkCache()
        cache._redis = mock_redis_client
        return cache

    @pytest.fixture
    def sample_link_data(self):
        """Sample link data for testing."""
        link_id = uuid4()
        expires_at = datetime.now(timezone.utc).replace(microsecond=0)
        return {
            "short_code": "abc123",
            "original_url": "https://example.com",
            "expires_at": expires_at,
            "link_id": link_id,
            "ttl_sec": 300,
        }

    async def test_get_cache_miss(self, cache, mock_redis_client):
        """Test get() returns None when key not in cache."""
        # Arrange
        mock_redis_client.client.get.return_value = None

        # Act
        result = await cache.get("abc123")

        # Assert
        mock_redis_client.client.get.assert_called_once_with("link:code:abc123")
        assert result is None

    async def test_get_cache_hit(self, cache, mock_redis_client, sample_link_data):
        """Test get() returns parsed data when key exists in cache."""
        # Arrange
        link_id = sample_link_data["link_id"]
        expires_at = sample_link_data["expires_at"]
        cached_data = {
            "original_url": sample_link_data["original_url"],
            "expires_at": expires_at.isoformat(),
            "link_id": str(link_id),
        }
        mock_redis_client.client.get.return_value = json.dumps(cached_data)

        # Act
        result = await cache.get("abc123")

        # Assert
        mock_redis_client.client.get.assert_called_once_with("link:code:abc123")
        assert result == cached_data

    async def test_get_cache_hit_no_expiration(self, cache, mock_redis_client):
        """Test get() handles cached data without expiration date."""
        # Arrange
        link_id = uuid4()
        cached_data = {
            "original_url": "https://example.com",
            "expires_at": None,
            "link_id": str(link_id),
        }
        mock_redis_client.client.get.return_value = json.dumps(cached_data)

        # Act
        result = await cache.get("abc123")

        # Assert
        assert result == cached_data
        assert result["expires_at"] is None

    async def test_set_with_expiration(self, cache, mock_redis_client, sample_link_data):
        """Test set() with expiration date."""
        # Arrange
        short_code = sample_link_data["short_code"]
        original_url = sample_link_data["original_url"]
        expires_at = sample_link_data["expires_at"]
        link_id = sample_link_data["link_id"]
        ttl_sec = sample_link_data["ttl_sec"]

        # Act
        await cache.set(
            short_code=short_code,
            original_url=original_url,
            expires_at=expires_at,
            link_id=link_id,
            ttl_sec=ttl_sec,
        )

        # Assert
        expected_key = "link:code:abc123"
        expected_data = {
            "original_url": original_url,
            "expires_at": expires_at.isoformat(),
            "link_id": str(link_id),
        }
        mock_redis_client.client.setex.assert_called_once_with(
            expected_key,
            ttl_sec,
            json.dumps(expected_data),
        )

    async def test_set_without_expiration(self, cache, mock_redis_client):
        """Test set() without expiration date."""
        # Arrange
        short_code = "abc123"
        original_url = "https://example.com"
        link_id = uuid4()
        ttl_sec = 300

        # Act
        await cache.set(
            short_code=short_code,
            original_url=original_url,
            expires_at=None,
            link_id=link_id,
            ttl_sec=ttl_sec,
        )

        # Assert
        expected_key = "link:code:abc123"
        expected_data = {
            "original_url": original_url,
            "expires_at": None,
            "link_id": str(link_id),
        }
        mock_redis_client.client.setex.assert_called_once_with(
            expected_key,
            ttl_sec,
            json.dumps(expected_data),
        )

    async def test_invalidate(self, cache, mock_redis_client):
        """Test invalidate() deletes key from cache."""
        # Arrange
        short_code = "abc123"

        # Act
        await cache.invalidate(short_code)

        # Assert
        mock_redis_client.client.delete.assert_called_once_with("link:code:abc123")

    async def test_make_key(self, cache):
        """Test internal _make_key method."""
        # Act
        key = cache._make_key("abc123")

        # Assert
        assert key == "link:code:abc123"