import asyncio
from typing import List

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker


@workflow.defn
class GreetingWorkflow:
    def __init__(self) -> None:
        self._pending_greetings: asyncio.Queue[str] = asyncio.Queue()
        self._exit = False

    @workflow.run
    async def run(self) -> List[str]:
        # Continually handle from queue or wait for exit to be received
        greetings: List[str] = []
        while not self._exit:
            # Wait for queue item or exit
            await workflow.wait_condition(
                lambda: not self._pending_greetings.empty() or self._exit
            )

            # Drain and process queue
            while not self._pending_greetings.empty():
                greetings.append(f"Hello, {self._pending_greetings.get_nowait()}")

        return greetings

    @workflow.signal
    async def submit_greeting(self, name: str) -> None:
        await self._pending_greetings.put(name)

    @workflow.signal
    def exit(self) -> None:
        self._exit = True


async def main():
    # Start client
    client = await Client.connect("http://localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-signal-task-queue",
        workflows=[GreetingWorkflow],
    ):

        # While the worker is running, use the client to start the workflow.
        # Note, in many production setups, the client would be in a completely
        # separate process from the worker.
        handle = await client.start_workflow(
            GreetingWorkflow.run,
            id="hello-signal-workflow-id",
            task_queue="hello-signal-task-queue",
        )

        # Send a few signals for names, then signal it to exit
        await handle.signal(GreetingWorkflow.submit_greeting, "user1")
        await handle.signal(GreetingWorkflow.submit_greeting, "user2")
        await handle.signal(GreetingWorkflow.submit_greeting, "user3")
        await handle.signal(GreetingWorkflow.exit)

        # Show result
        result = await handle.result()
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
