import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> str:
    # We'll wait for 3 seconds, heartbeating in between (like all long-running
    # activities should do), then return the greeting
    for _ in range(0, 3):
        print(f"Heartbeating activity")
        activity.heartbeat()
        time.sleep(1)
    return f"{input.greeting}, {input.name}!"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
            # Always set a heartbeat timeout for long-running activities
            heartbeat_timeout=timedelta(seconds=2),
        )


async def main():
    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-activity-heartbeating-task-queue",
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
            id="hello-activity-heartbeating-workflow-id",
            task_queue="hello-activity-heartbeating-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
