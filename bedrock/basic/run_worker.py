import asyncio
import concurrent.futures
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker
from workflows import BasicBedrockWorkflow

from bedrock.shared.activities import BedrockActivities
from util import get_temporal_config_path


async def main():
    # Create client connected to server at the given address
    config = ClientConfig.load_client_connect_config(
        config_file=str(get_temporal_config_path())
    )

    client = await Client.connect(**config)
    activities = BedrockActivities()

    # Run the worker
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue="bedrock-task-queue",
            workflows=[BasicBedrockWorkflow],
            activities=[activities.prompt_bedrock],
            activity_executor=activity_executor,
        )
        await worker.run()


if __name__ == "__main__":
    print("Starting worker")
    print("Then run 'python send_message.py \"<prompt>\"'")

    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())
