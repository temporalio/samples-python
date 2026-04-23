"""Starter that demonstrates standalone Nexus operation execution.

Unlike other Nexus samples that call operations from within a workflow, this
sample executes Nexus operations directly from client code using the standalone
Nexus operation APIs.
"""

import asyncio
import uuid
from datetime import timedelta

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from nexus_standalone_operations.service import (
    EchoInput,
    HelloInput,
    MyNexusService,
)

ENDPOINT_NAME = "nexus-standalone-operations-endpoint"


async def main() -> None:
    config = ClientConfig.load_client_connect_config()
    _ = config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Create a typed NexusClient bound to the endpoint and service.
    # The endpoint must be pre-created on the server (see README).
    nexus_client = client.create_nexus_client(
        service=MyNexusService, endpoint=ENDPOINT_NAME
    )

    # Start sync echo operation and await the result immediately.
    echo_result = await nexus_client.execute_operation(
        MyNexusService.echo,
        EchoInput(message="hello"),
        id=f"echo-{uuid.uuid4()}",
        schedule_to_close_timeout=timedelta(seconds=10),
    )
    print(f"Echo result: {echo_result.message}")

    # Start async (workflow-backed) hello operation and get a NexusOperationHandle.
    handle = await nexus_client.start_operation(
        MyNexusService.hello,
        HelloInput(name="World"),
        id=f"hello-{uuid.uuid4()}",
        schedule_to_close_timeout=timedelta(seconds=10),
    )

    print(f"\nStarted `MyNexusService.Hello`. OperationID: {handle.operation_id}")

    # Use the NexusOperationHandle to await the result of the operation.
    hello_result = await handle.result()
    print(f"`MyNexusService.Hello` result: {hello_result.greeting}")

    # List nexus operations.
    query = f'Endpoint = "{ENDPOINT_NAME}"'
    print("\nListing Nexus operations:")
    async for op in client.list_nexus_operations(query):
        print(
            f"  OperationId: {op.operation_id},",
            f" Operation: {op.operation},",
            f" Status: {op.status.name}",
        )

    # Count nexus operations.
    count = await client.count_nexus_operations(query)
    print(f"\nTotal Nexus operations: {count.count}")


if __name__ == "__main__":
    asyncio.run(main())
