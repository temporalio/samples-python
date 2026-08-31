"""Temporal connection settings shared by the worker and the starter.

Values are read from the environment so the same code runs against a local
plaintext dev server or Temporal Cloud. Set ``TEMPORAL_API_KEY`` to connect to
Temporal Cloud (which enables TLS); leave it unset for a plaintext connection.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    address: str
    namespace: str
    task_queue: str
    api_key: str | None

    @property
    def tls(self) -> bool:
        # Temporal Cloud requires TLS; a plaintext self-hosted server does not.
        return self.api_key is not None


def load_settings() -> Settings:
    """Build connection settings from TEMPORAL_* environment variables."""
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE")
    if not task_queue:
        raise RuntimeError("TEMPORAL_TASK_QUEUE must be set to a non-empty value")

    # Secret managers frequently preserve a trailing newline; strip it.
    api_key = os.environ.get("TEMPORAL_API_KEY")
    api_key = api_key.strip() if api_key else None

    return Settings(
        address=os.environ.get("TEMPORAL_ADDRESS") or "localhost:7233",
        namespace=os.environ.get("TEMPORAL_NAMESPACE") or "default",
        task_queue=task_queue,
        api_key=api_key or None,
    )
