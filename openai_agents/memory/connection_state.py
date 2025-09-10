"""Worker-level database connection state management.

WARNING: This implementation uses global state and is not safe for concurrent
testing (e.g., pytest-xdist). Run tests sequentially to avoid race conditions.
"""

import asyncpg
from typing import Optional


# Module-level connection state
_connection: Optional[asyncpg.Connection] = None


def set_worker_connection(connection: asyncpg.Connection) -> None:
    """Set the worker-level database connection."""
    global _connection
    _connection = connection


def get_worker_connection() -> asyncpg.Connection:
    """Get the worker-level database connection.

    Raises:
        RuntimeError: If no connection has been set.
    """
    if _connection is None:
        raise RuntimeError(
            "No worker-level database connection has been set. "
            "Call set_worker_connection() before using activities."
        )
    return _connection


def clear_worker_connection() -> None:
    """Clear the worker-level database connection."""
    global _connection
    _connection = None


def has_worker_connection() -> bool:
    """Check if a worker-level connection is available."""
    return _connection is not None
