import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from litellm_activity.activities import call_litellm
from litellm_activity.shared import TASK_QUEUE
from litellm_activity.workflow import LiteLLMWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[LiteLLMWorkflow],
        activities=[call_litellm],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
