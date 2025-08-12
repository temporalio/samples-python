import asyncio
import uuid

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from custom_metric.workflow import StartTwoActivitiesWorkflow
from util import get_temporal_config_path


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    client = await Client.connect(**config)

    await client.start_workflow(
        StartTwoActivitiesWorkflow.run,
        id="execute-activity-workflow-" + str(uuid.uuid4()),
        task_queue="custom-metric-task-queue",
    )


if __name__ == "__main__":
    asyncio.run(main())
