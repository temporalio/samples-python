import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from typing import NoReturn, Optional

from temporalio import activity, workflow
from temporalio.client import Client, WorkflowFailureError
from temporalio.common import RetryPolicy
from temporalio.exceptions import FailureError
from temporalio.worker import Worker


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> NoReturn:
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
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-exception-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        activity_executor=ThreadPoolExecutor(5),
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        #
        # This will raise a WorkflowFailureError with cause ActivityError with
        # cause ApplicationError with the error message and stack trace.
        try:
            await client.execute_workflow(
                GreetingWorkflow.run,
                "World",
                id="hello-exception-workflow-id",
                task_queue="hello-exception-task-queue",
            )
        except WorkflowFailureError as err:
            # Python does not support deserializing the traceback and putting it
            # back on the exception so we cannot repopulate the stack. Instead,
            # users can use the helper below to append the stack to the message.
            #
            # See https://github.com/temporalio/sdk-python/issues/58.
            append_temporal_stack(err)

            # Log the exception
            logging.exception("Got workflow failure")


# This is an example of appending the stack to every Temporal failure error
def append_temporal_stack(exc: Optional[BaseException]) -> None:
    while exc:
        # Only append if it doesn't appear already there
        if (
            isinstance(exc, FailureError)
            and exc.failure
            and exc.failure.stack_trace
            and len(exc.args) == 1
            and "\nStack:\n" not in exc.args[0]
        ):
            exc.args = (f"{exc}\nStack:\n{exc.failure.stack_trace.rstrip()}",)
        exc = exc.__cause__


if __name__ == "__main__":
    asyncio.run(main())
