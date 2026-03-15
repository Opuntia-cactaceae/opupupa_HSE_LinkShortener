import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from redis.exceptions import RedisError

from src.infrastructure.cache.redis_client import RedisClient


class TestRedisClient:
    

    async def test_connect_sets_client(self):
        client = RedisClient()
        mock_redis = AsyncMock()
        with patch('src.infrastructure.cache.redis_client.redis.from_url') as mock_from_url:
            mock_from_url.return_value = mock_redis
            await client.connect()
            mock_from_url.assert_called_once()
            assert client._client is mock_redis

    async def test_disconnect_closes_client(self):
        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis
        await client.disconnect()
        mock_redis.close.assert_awaited_once()
        assert client._client is None

    async def test_disconnect_does_nothing_if_not_connected(self):
        client = RedisClient()
        client._client = None
        await client.disconnect()  
        

    def test_client_property_returns_client_when_connected(self):
        client = RedisClient()
        mock_redis = AsyncMock()
        client._client = mock_redis
        assert client.client is mock_redis

    def test_client_property_raises_when_not_connected(self):
        client = RedisClient()
        client._client = None
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            _ = client.client

    async def test_connect_uses_settings_redis_url(self):
        client = RedisClient()
        mock_redis = AsyncMock()
        with patch('src.infrastructure.cache.redis_client.redis.from_url') as mock_from_url:
            mock_from_url.return_value = mock_redis
            await client.connect()