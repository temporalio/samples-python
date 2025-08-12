import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker


@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self._greeting = "<no greeting>"

    @workflow.run
    async def run(self, name: str) -> None:
        # Set the greeting, wait a couple of seconds, then change it
        self._greeting = f"Hello, {name}!"
        await asyncio.sleep(2)
        self._greeting = f"Goodbye, {name}!"

        # It's ok to end the workflow here. Queries work even after workflow
        # completion.

    @workflow.query
    def greeting(self) -> str:
        return self._greeting


async def main():
    # Get repo root - 1 level deep from root

    repo_root = Path(__file__).resolve().parent.parent

    config_file = repo_root / "temporal.toml"

    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    
    # Start client
    client = await Client.connect(**config)

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-query-task-queue",
        workflows=[GreetingWorkflow],
    ):

        # While the worker is running, use the client to start the workflow.
        # Note, in many production setups, the client would be in a completely
        # separate process from the worker.
        handle = await client.start_workflow(
            GreetingWorkflow.run,
            "World",
            id="hello-query-workflow-id",
            task_queue="hello-query-task-queue",
        )

        # Immediately query
        result = await handle.query(GreetingWorkflow.greeting)
        print(f"First greeting result: {result}")

        # Wait a few of seconds then query again. This works even if the
        # workflow has already completed.
        await asyncio.sleep(3)
        result = await handle.query(GreetingWorkflow.greeting)
        print(f"Second greeting result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
