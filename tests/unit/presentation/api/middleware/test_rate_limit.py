import pytest
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from fastapi import Request, HTTPException, status
from starlette.responses import Response
import redis.exceptions
from src.presentation.api.middleware.rate_limit import RateLimitMiddleware


class TestRateLimitMiddleware:
    """Unit tests for RateLimitMiddleware."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client with pipeline."""
        mock_client = AsyncMock()
        mock_pipeline = Mock()
        mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
        mock_pipeline.zcard = Mock(return_value=mock_pipeline)
        mock_pipeline.zadd = Mock(return_value=mock_pipeline)
        mock_pipeline.expire = Mock(return_value=mock_pipeline)
        mock_pipeline.execute = AsyncMock(return_value=[0, 0, 0, 0])  # default count=0
        mock_client.pipeline = Mock(return_value=mock_pipeline)
        return mock_client

    @pytest.fixture
    def middleware(self):
        """Create RateLimitMiddleware instance."""
        app = Mock()
        return RateLimitMiddleware(app)

    def test_init_sets_limits(self):
        """Test that __init__ sets correct limits."""
        app = Mock()
        middleware = RateLimitMiddleware(app)
        assert middleware._limits == {
            "POST:/auth/login": (5, 60),
            "POST:/links/shorten": (10, 60),
            "GET:/opupupa/": (100, 60),
            "default": (30, 60),
        }

    @pytest.mark.parametrize(
        "client_host, expected",
        [
            (("127.0.0.1", 12345), "127.0.0.1"),
            (None, "unknown"),
        ],
    )
    def test_get_client_ip(self, middleware, client_host, expected):
        """Test _get_client_ip returns client host or 'unknown'."""
        request = Mock(spec=Request)
        request.client = Mock(host=client_host[0] if client_host else None) if client_host else None
        result = middleware._get_client_ip(request)
        assert result == expected

    @pytest.mark.parametrize(
        "method, path, expected_key",
        [
            ("POST", "/auth/login", "POST:/auth/login"),
            ("POST", "/links/shorten", "POST:/links/shorten"),
            ("GET", "/opupupa/abc123", "GET:/opupupa/"),
            ("GET", "/opupupa/", "GET:/opupupa/"),
            ("GET", "/other", "default"),
            ("POST", "/other", "default"),
        ],
    )
    def test_get_path_pattern(self, middleware, method, path, expected_key):
        """Test _get_path_pattern returns correct limit key."""
        request = Mock(spec=Request)
        request.method = method
        request.url.path = path
        result = middleware._get_path_pattern(request)
        assert result == expected_key

    @pytest.mark.asyncio
    async def test_dispatch_options_skips(self, middleware):
        """Test dispatch skips rate limiting for OPTIONS method."""
        request = Mock(spec=Request)
        request.method = "OPTIONS"
        request.url.path = "/any"
        call_next = AsyncMock(return_value=Mock(spec=Response))

        with patch.object(middleware, '_get_client_ip') as mock_get_ip:
            result = await middleware.dispatch(request, call_next)
            mock_get_ip.assert_not_called()
        call_next.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_health_skips(self, middleware):
        """Test dispatch skips rate limiting for health endpoint."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/health"
        call_next = AsyncMock(return_value=Mock(spec=Response))

        with patch.object(middleware, '_get_client_ip') as mock_get_ip:
            result = await middleware.dispatch(request, call_next)
            mock_get_ip.assert_not_called()
        call_next.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_exceeded(self, middleware, mock_redis_client):
        """Test dispatch raises 429 when rate limit exceeded."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/auth/login"
        request.client = Mock(host="192.168.1.1")
        call_next = AsyncMock()

        # Set count >= limit (limit=5)
        mock_pipeline = mock_redis_client.pipeline.return_value
        mock_pipeline.execute.return_value = [0, 5, 0, 0]  # count = 5

        with patch('src.presentation.api.middleware.rate_limit.redis_client._client', mock_redis_client):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert json.loads(response.body) == {"detail": "Rate limit exceeded"}
            assert response.headers["Retry-After"] == "60"

        # Ensure pipeline methods called
        mock_pipeline.zremrangebyscore.assert_called()
        mock_pipeline.zcard.assert_called()
        mock_pipeline.zadd.assert_called()
        mock_pipeline.expire.assert_called()
        mock_pipeline.execute.assert_awaited()
        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatch_redis_exception(self, middleware, mock_redis_client):
        """Test dispatch raises 503 when Redis fails."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/some"
        request.client = Mock(host="192.168.1.1")
        call_next = AsyncMock()

        mock_pipeline = mock_redis_client.pipeline.return_value
        mock_pipeline.execute.side_effect = redis.exceptions.RedisError("Redis down")

        with patch('src.presentation.api.middleware.rate_limit.redis_client._client', mock_redis_client):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert json.loads(response.body) == {"detail": "Service temporarily unavailable"}

        call_next.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dispatch_success(self, middleware, mock_redis_client):
        """Test dispatch allows request when under limit."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/links/shorten"
        request.client = Mock(host="192.168.1.1")
        mock_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        # count < limit (limit=10)
        mock_pipeline = mock_redis_client.pipeline.return_value
        mock_pipeline.execute.return_value = [0, 3, 0, 0]  # count = 3

        with patch('src.presentation.api.middleware.rate_limit.redis_client._client', mock_redis_client):
            response = await middleware.dispatch(request, call_next)
            assert response is mock_response

        mock_pipeline.execute.assert_awaited()
        call_next.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_unknown_client_ip(self, middleware, mock_redis_client):
        """Test dispatch works when client IP is unknown."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/other"
        request.client = None
        mock_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        mock_pipeline = mock_redis_client.pipeline.return_value
        mock_pipeline.execute.return_value = [0, 1, 0, 0]

        with patch('src.presentation.api.middleware.rate_limit.redis_client._client', mock_redis_client):
            response = await middleware.dispatch(request, call_next)
            assert response is mock_response

        # Ensure limit key contains "unknown"
        mock_redis_client.pipeline.assert_called()
        # We could check that _get_client_ip returned "unknown" but we patched redis client only.
        # Instead we can assert that pipeline was called (already).