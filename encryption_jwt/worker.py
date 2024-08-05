import asyncio
import dataclasses
import os

import temporalio.converter
from temporalio import workflow
from temporalio.client import Client, TLSConfig
from temporalio.worker import Worker

from encryption_jwt.codec import EncryptionCodec


temporal_address = "localhost:7233"
if os.environ.get("TEMPORAL_ADDRESS"):
    temporal_address = os.environ["TEMPORAL_ADDRESS"]

temporal_namespace = "default"
if os.environ.get("TEMPORAL_NAMESPACE"):
    temporal_namespace = os.environ["TEMPORAL_NAMESPACE"]

temporal_tls_cert = None
if os.environ.get("TEMPORAL_TLS_CERT"):
    temporal_tls_cert_path = os.environ["TEMPORAL_TLS_CERT"]
    with open(temporal_tls_cert_path, "rb") as f:
        temporal_tls_cert = f.read()

temporal_tls_key = None
if os.environ.get("TEMPORAL_TLS_KEY"):
    temporal_tls_key_path = os.environ["TEMPORAL_TLS_KEY"]
    with open(temporal_tls_key_path, "rb") as f:
        temporal_tls_key = f.read()


@workflow.defn(name="Workflow")
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return f"Hello, {name}"


interrupt_event = asyncio.Event()


async def main():
    # Connect client
    client = await Client.connect(
        temporal_address,
        # Use the default converter, but change the codec
        data_converter=dataclasses.replace(
            temporalio.converter.default(), payload_codec=EncryptionCodec()
        ),
        namespace=temporal_namespace,
        tls=TLSConfig(
            client_cert=temporal_tls_cert,
            client_private_key=temporal_tls_key,
        ) if temporal_tls_cert and temporal_tls_key else False
    )

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="encryption-task-queue",
        workflows=[GreetingWorkflow],
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
