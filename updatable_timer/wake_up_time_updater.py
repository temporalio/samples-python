import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from updatable_timer.workflow import Workflow


async def main(client: Optional[Client] = None):
    logging.basicConfig(level=logging.INFO)

    if not client:
        config_dict = ClientConfigProfile.load().to_dict()
        config_dict.setdefault("address", "localhost:7233")
        config = ClientConfigProfile.from_dict(config_dict)
        client = await Client.connect(**config.to_client_connect_config())

    handle = client.get_workflow_handle(workflow_id="updatable-timer-workflow")
    # signal workflow about the wake up time change
    await handle.signal(
        Workflow.update_wake_up_time,
        (datetime.now() + timedelta(seconds=10)).timestamp(),
    )

    logging.info("Updated wake up time to 10 seconds from now")


if __name__ == "__main__":
    asyncio.run(main())
