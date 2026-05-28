from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class Downstream:
    """A counter with a fixed capacity. Thread-safe."""

    def __init__(self, allowed_connections: int, name: str = "downstream") -> None:
        self.allowed_connections = allowed_connections
        self.name = name
        self.currently_connected = 0
        self.connection_pool = threading.Lock()
        logger.info(
            "Downstream ready: name=%s allowed_connections=%d",
            name,
            allowed_connections,
        )

    def increment(self) -> bool:
        """allow one connection. Returns False if at capacity."""
        with self.connection_pool:
            if self.currently_connected >= self.allowed_connections:
                return False
            self.currently_connected += 1
            return True

    def decrement(self) -> None:
        """Release one slot. Floored at 0 so a buggy caller can't go negative."""
        with self.connection_pool:
            self.currently_connected = max(0, self.currently_connected - 1)
