import asyncio
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
async def compose_greeting(input: ComposeGreetingInput) -> str:
    return f"{input.greeting}, {input.name}!"


@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self.exit_requested = False

    @workflow.run
    async def run(self, name: str) -> str:
        # Invoke activity (or do other meaningful work)
        result = await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Continue as new every 2 seconds until we are told to complete. This is
        # just a demonstration. In production code you might want to continue as
        # new when the history is growing too large. Continue as new is
        # essentially a workflow restart (though another workflow can be used).
        try:
            await workflow.wait_condition(lambda: self.exit_requested, timeout=2)
            print("Exit requested")
            return result
        except asyncio.TimeoutError:
            print("Continuing as new")
            workflow.continue_as_new(name)

    @workflow.signal
    def request_exit(self) -> None:
        self.exit_requested = True


async def main():
    # Start client
    client = await Client.connect("http://localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-continue-as-new-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
    ):

        # While the worker is running, use the client to start the workflow.
        # Note, in many production setups, the client would be in a completely
        # separate process from the worker.
        handle = await client.start_workflow(
            GreetingWorkflow.run,
            "World",
            id="hello-continue-as-new-workflow-id",
            task_queue="hello-continue-as-new-task-queue",
        )

        # Now wait 5 seconds and request exit
        await asyncio.sleep(5)
        print("Requesting exit")
        await handle.signal(GreetingWorkflow.request_exit)
        result = await handle.result()
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
