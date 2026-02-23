import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

# This sample is very similar to hello_activity.py. The difference is that whereas in
# hello_activity.py the activity is orchestrated by a workflow, in this sample the activity is
# executed directly by a client ("standalone activity").


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


# This is just a normal activity. You could invoke it from a workflow but, in this sample, we are
# invoking it directly as a standalone activity.
@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"


async def my_client_code(client: Client):
    # client.execute_activity starts the activity, and then uses a long-poll to wait for the
    # activity to be completed by the worker.
    result = await client.execute_activity(
        compose_greeting,
        args=[ComposeGreetingInput("Hello", "World")],
        id="my-standalone-activity-id",
        task_queue="hello-standalone-activity-task-queue",
        start_to_close_timeout=timedelta(seconds=10),
    )
    print(f"Activity result: {result}")

    activities = client.list_activities(
        query="TaskQueue = 'hello-standalone-activity-task-queue'"
    )
    print("ListActivity results:")
    async for info in activities:
        print(f"\tActivityID: {info.activity_id}, Type: {info.activity_type}, Status: {info.status}")

    count_result = await client.count_activities(
        query="TaskQueue = 'hello-standalone-activity-task-queue'"
    )
    print(f"Total activities: {count_result.count}")


async def main():
    # Uncomment the lines below to see logging output
    # import logging
    # logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    client = await Client.connect(**config)

    # Run a worker for the activity
    async with Worker(
        client,
        task_queue="hello-standalone-activity-task-queue",
        activities=[compose_greeting],
    ):
        # While the worker is running, use the client to execute the activity.
        await my_client_code(client)


if __name__ == "__main__":
    asyncio.run(main())
