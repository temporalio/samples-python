import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import NoReturn

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> NoReturn:
    # Always raise exception
    raise RuntimeError(f"Greeting exception: {input.greeting}, {input.name}!")


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
            # We'll only retry once
            retry_policy=RetryPolicy(maximum_attempts=2),
        )


async def main():
    # Start client
    client = await Client.connect("http://localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-exception-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        #
        # This will raise a WorkflowFailureError with cause ActivityError with
        # cause ApplicationError with the error message and stack trace.
        await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id="hello-exception-workflow-id",
            task_queue="hello-exception-task-queue",
        )


if __name__ == "__main__":
    asyncio.run(main())
