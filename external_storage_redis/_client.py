"""Redis storage driver client abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta


class RedisStorageDriverClient(ABC):
    """Abstract base class for the Redis operations used by the driver."""

    @abstractmethod
    async def get(self, *, key: str) -> bytes | None:
        """Return the raw bytes stored for *key*, or ``None`` if absent."""

    @abstractmethod
    async def set_if_absent(
        self,
        *,
        key: str,
        data: bytes,
        ttl: timedelta | None = None,
    ) -> bool:
        """Store *data* under *key* only if the key does not already exist.

        Args:
            key: Redis key to store.
            data: Serialized payload bytes.
            ttl: Optional expiration to apply only when the value is inserted.

        Returns:
            ``True`` if the value was inserted, ``False`` if the key already
            existed.
        """
