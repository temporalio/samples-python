import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from threading import Thread

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


class GreetingComposer:
    def __init__(self, client: Client, loop: asyncio.AbstractEventLoop) -> None:
        self.client = client
        self.loop = loop

    @activity.defn
    def compose_greeting(self, input: ComposeGreetingInput) -> str:
        # Make a thread to complete this externally. This could be done in
        # a completely different process or system.
        print("Completing activity asynchronously")
        Thread(
            target=self.complete_greeting,
            args=(activity.info().task_token, input),
        ).start()

        # Raise the complete-async error which will complete this function but
        # does not consider the activity complete from the workflow perspective
        activity.raise_complete_async()

    def complete_greeting(self, task_token: bytes, input: ComposeGreetingInput) -> None:
        # Let's wait three seconds, heartbeating each second. Note, heartbeating
        # during async activity completion is done via the client directly. It
        # is often important to heartbeat so the server can know when an
        # activity has crashed.
        handle = self.client.get_async_activity_handle(task_token=task_token)
        for _ in range(0, 3):
            print("Waiting one second...")
            asyncio.run_coroutine_threadsafe(handle.heartbeat(), self.loop).result()
            time.sleep(1)

        # Complete using the handle
        asyncio.run_coroutine_threadsafe(
            handle.complete(f"{input.greeting}, {input.name}!"), self.loop
        ).result()


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        # Use execute_activity_method which lets us reference a method instead
        # of a function
        return await workflow.execute_activity_method(
            GreetingComposer.compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
            heartbeat_timeout=timedelta(seconds=2),
        )


async def main():
    # Start client
    client = await Client.connect("localhost:7233")

    loop = asyncio.get_event_loop()

    # Run a worker for the workflow
    composer = GreetingComposer(client, loop)
    async with Worker(
        client,
        task_queue="hello-async-activity-completion-task-queue",
        workflows=[GreetingWorkflow],
        activities=[composer.compose_greeting],
        activity_executor=ThreadPoolExecutor(5),
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id="hello-async-activity-completion-workflow-id",
            task_queue="hello-async-activity-completion-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
