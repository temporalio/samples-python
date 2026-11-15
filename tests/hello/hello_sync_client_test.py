import asyncio

import pytest
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from hello.hello_sync_client import greet


async def test_greet_from_sync_code(client: Client, monkeypatch: pytest.MonkeyPatch):
    # Connect the sample's own client to the test environment (local or
    # time-skipping), rather than sharing a client across event loops.
    monkeypatch.setattr(
        ClientConfig,
        "load_client_connect_config",
        lambda: {
            "target_host": client.service_client.config.target_host,
            "namespace": client.namespace,
        },
    )

    def call_from_sync_code():
        # Repeated calls create fresh loops and must both complete successfully.
        assert greet("World") == "Hello, World!"
        assert greet("Temporal") == "Hello, Temporal!"

    # Keep the test environment's event loop available while the synchronous
    # caller blocks waiting for the workflow result on its own thread.
    await asyncio.to_thread(call_from_sync_code)
