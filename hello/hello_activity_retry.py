import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> str:
    print(f"Invoking activity, attempt number {activity.info().attempt}")
    # Fail the first 3 attempts, succeed the 4th
    if activity.info().attempt < 4:
        raise RuntimeError("Intentional failure")
    return f"{input.greeting}, {input.name}!"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        # By default activities will retry, backing off an initial interval and
        # then using a coefficient of 2 to increase the backoff each time after
        # for an unlimited amount of time and an unlimited number of attempts.
        # We'll keep those defaults except we'll set the maximum interval to
        # just 2 seconds.
        # @@@SNIPSTART python-activity-retry
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_interval=timedelta(seconds=2)),
        )
        # @@@SNIPEND


async def main():
    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-activity-retry-task-queue",
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
            id="hello-activity-retry-workflow-id",
            task_queue="hello-activity-retry-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
