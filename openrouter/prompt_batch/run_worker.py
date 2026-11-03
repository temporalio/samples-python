import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from openrouter.activities import OpenRouterActivities, build_client
from openrouter.prompt_batch.workflow import PromptBatchWorkflow
from openrouter.shared import PROMPT_BATCH_TASK_QUEUE


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # One OpenRouter client for the Worker's lifetime, shared by every
    # concurrent Activity. Reads OPENROUTER_API_KEY from the environment.
    activities = OpenRouterActivities(build_client())

    worker = Worker(
        client,
        task_queue=PROMPT_BATCH_TASK_QUEUE,
        workflows=[PromptBatchWorkflow],
        activities=[activities.call_openrouter],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
