import asyncio
import uuid
from typing import Optional

from temporalio.client import Client

from sleep_for_days import TASK_QUEUE
from sleep_for_days.workflows import SleepForDaysWorkflow


async def main(client: Optional[Client] = None):
    client = client or await Client.connect("localhost:7233")
    wf_handle = await client.start_workflow(
        SleepForDaysWorkflow.run,
        id=f"sleep-for-days-workflow-id-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
    )
    # Wait for workflow completion (runs indefinitely until it receives a signal)
    print(await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
