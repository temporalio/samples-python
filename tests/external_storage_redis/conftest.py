"""Shared fixtures for Redis external storage tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import fakeredis.aioredis
import pytest
import pytest_asyncio

from external_storage_redis import RedisStorageDriverClient
from external_storage_redis.redis_asyncio import new_redis_asyncio_client

if TYPE_CHECKING:
    from redis.asyncio.client import Redis

KEY_PREFIX = "test:payloads"


@pytest_asyncio.fixture
async def redis_asyncio_client() -> AsyncIterator[Redis]:
    """Yield a fake Redis client with an empty database for each test."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    await client.flushdb()
    try:
        yield client
    finally:
        aclose = getattr(client, "aclose", None)
        if aclose is not None:
            await aclose()
        else:
            await client.close()


@pytest.fixture
def driver_client(redis_asyncio_client: Redis) -> RedisStorageDriverClient:
    """Wrap the redis.asyncio client in a RedisStorageDriverClient adapter."""
    return new_redis_asyncio_client(redis_asyncio_client)
