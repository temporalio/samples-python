import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


@dataclass
class SayHelloInput:
    greeting: str
    name: str


@activity.defn
async def say_hello(input: SayHelloInput) -> str:
    return f"Hello, {input.name}!"


@workflow.defn
class SayHello:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            say_hello,
            SayHelloInput("Hello", name),
            schedule_to_close_timeout=timedelta(seconds=5),
        )


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Run the worker
    worker = Worker(
        client, task_queue="my-task-queue", workflows=[SayHello], activities=[say_hello]
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
