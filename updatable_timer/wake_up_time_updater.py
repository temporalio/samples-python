import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from temporalio.client import Client

from updatable_timer.workflow import Workflow


async def main(client: Optional[Client] = None):
    logging.basicConfig(level=logging.INFO)

    client = client or await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id="updatable-timer-workflow")
    # signal workflow about the wake up time change
    await handle.signal(
        Workflow.update_wake_up_time,
        (datetime.now() + timedelta(seconds=10)).timestamp(),
    )

    logging.info("Updated wake up time to 10 seconds from now")


if __name__ == "__main__":
    asyncio.run(main())
