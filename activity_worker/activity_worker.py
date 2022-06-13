import asyncio
import random
import string

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

task_queue = "say-hello-task-queue"
workflow_name = "say-hello-workflow"
activity_name = "say-hello-activity"


@activity.defn(name=activity_name)
async def say_hello_activity(name: str) -> str:
    return f"Hello, {name}!"


async def main():
    # Create client to localhost on default namespace
    client = await Client.connect("http://localhost:7233")

    # Run activity worker
    async with Worker(client, task_queue=task_queue, activities=[say_hello_activity]):
        # Run the Go workflow
        workflow_id = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=30)
        )
        result = await client.execute_workflow(
            workflow_name, "Temporal", id=workflow_id, task_queue=task_queue
        )
        # Print out "Hello, Temporal!"
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
