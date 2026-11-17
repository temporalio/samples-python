import asyncio
from uuid import uuid4

from temporalio.client import Client

from config import caller_data_converter
from service import CALLER_NAMESPACE, ENDPOINTS
from workflows import CallerWorkflow


async def main() -> None:
    client = await Client.connect(
        "localhost:7233",
        namespace=CALLER_NAMESPACE,
        data_converter=caller_data_converter(),
    )
    handle = await client.start_workflow(
        CallerWorkflow.run,
        "Hello from Nexus",
        id=f"nexus-serialization-{uuid4()}",
        task_queue=CALLER_NAMESPACE,
    )
    print(f"Started workflow: ID={handle.id} RunID={handle.result_run_id}", flush=True)
    results = await handle.result()
    for endpoint in ENDPOINTS:
        result = results[endpoint]
        print(f'{endpoint}: sync="{result.sync}" async="{result.async_result}"')


if __name__ == "__main__":
    asyncio.run(main())
