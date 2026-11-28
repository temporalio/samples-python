from __future__ import annotations

import os
from dataclasses import dataclass

from temporalio.client import Client, StreamConfig
from temporalio.envconfig import ClientConfig
from temporalio_streams_redis import RedisStreamStore

TASK_QUEUE = "streams-redis-task-queue"


@dataclass
class AgentEvent:
    kind: str
    text: str


LAST_EVENT = AgentEvent("status", "Done")


async def connect() -> Client:
    """Share one Store configuration between the client and its Workers."""
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    store = RedisStreamStore(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    return await Client.connect(**config, stream_config=StreamConfig(stores=[store]))
