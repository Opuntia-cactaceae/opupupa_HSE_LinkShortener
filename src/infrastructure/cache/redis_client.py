from typing import Optional

import redis.asyncio as redis

from ..settings import settings


class RedisClient:
    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        self._client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client not connected")
        return self._client


redis_client = RedisClient()