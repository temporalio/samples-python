"""Temporal connection settings shared by the worker and the starter.

Set ``TEMPORAL_API_KEY`` to connect to Temporal Cloud (which enables TLS); leave
it unset for a plaintext dev server.
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
        return self.api_key is not None


def load_settings() -> Settings:
    namespace = os.environ.get("TEMPORAL_NAMESPACE") or "default"
    api_key = os.environ.get("TEMPORAL_API_KEY")
    return Settings(
        address=os.environ.get("TEMPORAL_ADDRESS") or f"{namespace}.tmprl.cloud:7233",
        namespace=namespace,
        task_queue=os.environ.get("TEMPORAL_TASK_QUEUE") or "gcp-cloud-run",
        # Secret managers frequently preserve a trailing newline; strip it.
        api_key=api_key.strip() if api_key else None,
    )
