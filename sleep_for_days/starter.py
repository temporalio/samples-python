import asyncio
import uuid
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from sleep_for_days import TASK_QUEUE
from sleep_for_days.workflows import SleepForDaysWorkflow


async def main(client: Optional[Client] = None):
    if not client:
        config_dict = ClientConfigProfile.load().to_dict()
        config_dict.setdefault("address", "localhost:7233")
        config = ClientConfigProfile.from_dict(config_dict)
        client = await Client.connect(**config.to_client_connect_config())
    wf_handle = await client.start_workflow(
        SleepForDaysWorkflow.run,
        id=f"sleep-for-days-workflow-id-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
    )
    # Wait for workflow completion (runs indefinitely until it receives a signal)
    print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
