import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from .redis_client import redis_client


class LinkCache:
    def __init__(self) -> None:
        self._redis = redis_client

    def _make_key(self, short_code: str) -> str:
        return f"link:code:{short_code}"

    async def get(self, short_code: str) -> Optional[dict]:
        key = self._make_key(short_code)
        data = await self._redis.client.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def set(
        self,
        short_code: str,
        original_url: str,
        expires_at: Optional[datetime],
        link_id: UUID,
        ttl_sec: int,
    ) -> None:
        key = self._make_key(short_code)
        data = {
            "original_url": original_url,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "link_id": str(link_id),
        }
        await self._redis.client.setex(key, ttl_sec, json.dumps(data))

    async def invalidate(self, short_code: str) -> None:
        key = self._make_key(short_code)
        await self._redis.client.delete(key)