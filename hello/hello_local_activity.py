import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from util import get_temporal_config_path


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> str:
    return f"{input.greeting}, {input.name}!"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_local_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )


async def main():
    # Start client
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-local-activity-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        activity_executor=ThreadPoolExecutor(5),
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id="hello-local-activity-workflow-id",
            task_queue="hello-local-activity-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
