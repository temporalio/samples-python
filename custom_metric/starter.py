import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from custom_metric.workflow import StartTwoActivitiesWorkflow


async def main():
    config_dict = ClientConfigProfile.load().to_dict()
    config_dict.setdefault("address", "localhost:7233")
    config = ClientConfigProfile.from_dict(config_dict)
    client = await Client.connect(**config.to_client_connect_config())

    await client.start_workflow(
        StartTwoActivitiesWorkflow.run,
        id="execute-activity-workflow-" + str(uuid.uuid4()),
        task_queue="custom-metric-task-queue",
    )


if __name__ == "__main__":
    asyncio.run(main())
