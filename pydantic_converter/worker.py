import asyncio
import logging
from datetime import datetime, timedelta
from ipaddress import IPv4Address
from typing import List

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from util import get_temporal_config_path

# Always pass through external modules to the sandbox that you know are safe for
# workflow use
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel
    from temporalio.contrib.pydantic import pydantic_data_converter


class MyPydanticModel(BaseModel):
    some_ip: IPv4Address
    some_date: datetime


@activity.defn
async def my_activity(models: List[MyPydanticModel]) -> List[MyPydanticModel]:
    activity.logger.info("Got models in activity: %s" % models)
    return models


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, models: List[MyPydanticModel]) -> List[MyPydanticModel]:
        workflow.logger.info("Got models in workflow: %s" % models)
        return await workflow.execute_activity(
            my_activity, models, start_to_close_timeout=timedelta(minutes=1)
        )


interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    # Connect client using the Pydantic converter
    client = await Client.connect(
        **config,
        data_converter=pydantic_data_converter,
    )

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="pydantic_converter-task-queue",
        workflows=[MyWorkflow],
        activities=[my_activity],
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
