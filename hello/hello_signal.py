import asyncio
from typing import List

from temporalio import workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile
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
        while True:
            # Wait for queue item or exit
            await workflow.wait_condition(
                lambda: not self._pending_greetings.empty() or self._exit
            )

            # Drain and process queue
            while not self._pending_greetings.empty():
                greetings.append(f"Hello, {self._pending_greetings.get_nowait()}")

            # Exit if complete
            if self._exit:
                return greetings

    @workflow.signal
    async def submit_greeting(self, name: str) -> None:
        await self._pending_greetings.put(name)

    @workflow.signal
    def exit(self) -> None:
        self._exit = True


async def main():
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    # Start client
    client = await Client.connect(**config.to_client_connect_config())

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
