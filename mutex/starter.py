from temporalio.client import Client
import logging
from uuid import uuid4
from workflow import SampleWorkflowWithMutex
import asyncio


async def main():
    # set up logging facility
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    # Start client
    client = await Client.connect("localhost:7233")

    resource_id = uuid4()

    print("starting first workflow")
    workflow_1 = client.execute_workflow(
        SampleWorkflowWithMutex.run,
        str(resource_id),
        id="sample-workflow-with-mutex-1-workflow-id",
        task_queue="mutex-task-queue",
    )
    print("starting second workflow")
    workflow_2 = client.execute_workflow(
        SampleWorkflowWithMutex.run,
        str(resource_id),
        id="sample-workflow-with-mutex-2-workflow-id",
        task_queue="mutex-task-queue",
    )
    results = await asyncio.gather(workflow_1, workflow_2)
    print("results:", *results)


if __name__ == "__main__":
    asyncio.run(main())
