import asyncio
import dataclasses
import os

import temporalio.converter
from temporalio.client import Client, TLSConfig

from encryption_jwt.codec import EncryptionCodec
from encryption_jwt.worker import GreetingWorkflow

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

    # Run workflow
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        "Temporal",
        id=f"encryption-workflow-id",
        task_queue="encryption-task-queue",
    )
    print(f"Workflow result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
