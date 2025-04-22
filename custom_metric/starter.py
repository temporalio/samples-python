import asyncio
import uuid

from temporalio.client import Client

from custom_metric.workflow import StartTwoActivitiesWorkflow


async def main():

    client = await Client.connect(
        "localhost:7233",
    )

    await client.start_workflow(
        StartTwoActivitiesWorkflow.run,
        id="execute-activity-workflow-" + str(uuid.uuid4()),
        task_queue="custom-metric-task-queue",
    )


if __name__ == "__main__":
    asyncio.run(main())
