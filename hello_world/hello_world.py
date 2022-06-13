import asyncio
import logging
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


# Basic activity that logs and does string concatenation
@activity.defn
async def say_hello_activity(name: str) -> str:
    activity.logger.info("Running activity with parameter %s" % name)
    return f"Hello, {name}!"


# Basic workflow that logs and invokes an activity
@workflow.defn
class SayHelloWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)
        return await workflow.execute_activity(
            say_hello_activity, name, start_to_close_timeout=timedelta(seconds=10)
        )


async def main():
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect("http://localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="my-task-queue",
        workflows=[SayHelloWorkflow],
        activities=[say_hello_activity],
    ):

        # While the worker is running, use the client ro tun the workflow and
        # print out its result
        result = await client.execute_workflow(
            SayHelloWorkflow.run,
            "Temporal",
            id="my-workflow-id",
            task_queue="my-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
