"""redis.asyncio adapter for the Redis storage driver client."""

from __future__ import annotations

import math
from datetime import timedelta
from typing import TYPE_CHECKING

from external_storage_redis._client import RedisStorageDriverClient

if TYPE_CHECKING:
    from redis.asyncio.client import Redis


class _RedisAsyncioStorageDriverClient(RedisStorageDriverClient):
    """Adapter that wraps a ``redis.asyncio.Redis`` client.

    The wrapped client must be configured for binary-safe reads and writes,
    which means ``decode_responses`` must remain disabled.
    """

    def __init__(self, client: Redis) -> None:
        """Wrap a ``redis.asyncio.Redis`` client."""
        self._client = client

    async def get(self, *, key: str) -> bytes | None:
        """Fetch raw bytes for *key* from Redis."""
        value = await self._client.get(key)
        if value is None:
            return None
        if not isinstance(value, bytes):
            raise TypeError(
                "redis.asyncio client must be configured with decode_responses=False"
            )
        return value

    async def set_if_absent(
        self,
        *,
        key: str,
        data: bytes,
        ttl: timedelta | None = None,
    ) -> bool:
        """Atomically set *key* only when it is absent."""
        ttl_ms = None
        if ttl is not None:
            ttl_ms = max(1, math.ceil(ttl.total_seconds() * 1000))
        result = await self._client.set(key, data, px=ttl_ms, nx=True)
        return bool(result)


def new_redis_asyncio_client(client: Redis) -> RedisStorageDriverClient:
    """Create a driver client from a ``redis.asyncio.Redis`` instance."""
    return _RedisAsyncioStorageDriverClient(client)
