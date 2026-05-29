from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class FakeDatabaseConnectionPool:
    """Pretend connection pool with a fixed capacity, backed by a Semaphore."""

    def __init__(self, allowed_connections: int, name: str = "db") -> None:
        self.allowed_connections = allowed_connections
        self.name = name
        self._connection_pool = threading.BoundedSemaphore(allowed_connections)
        logger.info(
            "FakeDatabaseConnectionPool ready: name=%s allowed_connections=%d",
            name,
            allowed_connections,
        )

    def acquire(self, blocking: bool = True) -> bool:
        """Claim a connection. When blocking, waits until one is free."""
        return self._connection_pool.acquire(blocking=blocking)

    def release(self) -> None:
        """Return a connection to the pool."""
        self._connection_pool.release()

    @property
    def in_use(self) -> int:
        """Derived from the semaphore — single source of truth."""
        return self.allowed_connections - self._connection_pool._value
