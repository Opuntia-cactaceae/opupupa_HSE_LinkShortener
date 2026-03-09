import time

import redis.exceptions
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from ....infrastructure.cache.redis_client import redis_client
from ....infrastructure.settings import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._limits = {
            "POST:/auth/login": (5, 60),
            "POST:/links/shorten": (10, 60),
            "GET:/opupupa/": (100, 60),
            "default": (30, 60),
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path == "/health":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        path_pattern = self._get_path_pattern(request)

        limit_key = f"rate_limit:{client_ip}:{path_pattern}"
        limit, window_sec = self._limits.get(path_pattern, self._limits["default"])

        try:
            now = time.time()
            member = str(time.time_ns())
            window_start = now - window_sec

            pipe = redis_client.client.pipeline()
            pipe.zremrangebyscore(limit_key, "-inf", window_start)
            pipe.zcard(limit_key)
            pipe.zadd(limit_key, {member: now})
            pipe.expire(limit_key, window_sec)
            results = await pipe.execute()

            count = results[1]
            if count >= limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(window_sec)},
                )
        except redis.exceptions.RedisError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Service temporarily unavailable"},
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _get_path_pattern(self, request: Request) -> str:
        method = request.method
        path = request.url.path

        if method == "POST" and path == "/auth/login":
            return "POST:/auth/login"

        if method == "POST" and path == "/links/shorten":
            return "POST:/links/shorten"

        if method == "GET" and path.startswith("/opupupa/"):
            return "GET:/opupupa/"

        return "default"