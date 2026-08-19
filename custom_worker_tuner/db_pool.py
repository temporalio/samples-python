from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class FakeDatabaseConnectionPool:
    """Pretend connection pool with a fixed capacity, backed by an asyncio.Semaphore."""

    def __init__(self, allowed_connections: int, name: str = "db") -> None:
        self.allowed_connections = allowed_connections
        self.name = name
        self._connection_pool = asyncio.Semaphore(allowed_connections)
        logger.info(
            "FakeDatabaseConnectionPool ready: name=%s allowed_connections=%d",
            name,
            allowed_connections,
        )

    async def acquire(self) -> None:
        """Claim a connection, awaiting until one is free."""
        await self._connection_pool.acquire()

    def try_acquire(self) -> bool:
        """Non-blocking claim, try_reserve_slot will call this 
        if the pool is full - it will return false
        if it is not full - total pool connections - 1 and slot granted to activity
        """
        if self._connection_pool.locked():
            return False
        self._connection_pool._value -= 1
        return True

    def release(self) -> None:
        """Return a connection to the pool."""
        self._connection_pool.release()

    @property
    def in_use(self) -> int:
        """Derived from the semaphore — single source of truth."""
        return self.allowed_connections - self._connection_pool._value

    @property
    def queued(self) -> int:
        """How many tasks are parked waiting for a free slot."""
        waiters = self._connection_pool._waiters
        if not waiters:
            return 0
        return sum(1 for w in waiters if not w.done())
