import asyncio
import uuid

from temporalio import workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return f"Hello, {name}!"


async def _execute_greeting(name: str) -> str:
    # Create and use the client on the same event loop. Do not cache this client
    # and reuse it across calls to asyncio.run(), which creates a new loop.
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)
    task_queue = f"hello-sync-client-{uuid.uuid4()}"

    # Keep the sample self-contained by running a worker here. In a production
    # application, workers usually run in a separate process on a shared queue.
    async with Worker(client, task_queue=task_queue, workflows=[GreetingWorkflow]):
        return await client.execute_workflow(
            GreetingWorkflow.run,
            name,
            id=f"hello-sync-client-{uuid.uuid4()}",
            task_queue=task_queue,
        )


def greet(name: str) -> str:
    """Execute a workflow from synchronous code and wait for its result."""
    # This is the boundary between the synchronous application and the async SDK.
    # Call it from a thread without a running event loop. In an async application,
    # await the async SDK directly instead.
    return asyncio.run(_execute_greeting(name))


def main() -> None:
    # Existing synchronous application code does not need async/await.
    print(f"Result: {greet('World')}")


if __name__ == "__main__":
    main()
