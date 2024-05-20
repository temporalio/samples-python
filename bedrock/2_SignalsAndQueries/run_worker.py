import asyncio
import concurrent.futures
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from activities import prompt_bedrock
from workflows import SignalQueryBedrockWorkflow


async def run_worker(client):
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue="bedrock-task-queue",
            workflows=[SignalQueryBedrockWorkflow],
            activities=[prompt_bedrock],
            activity_executor=activity_executor,
        )
        await worker.run()


async def main():
    logging.basicConfig(level=logging.INFO)

    # temporal server start-dev
    client = await Client.connect("localhost:7233")

    await run_worker(client)

if __name__ == "__main__":
    print("Starting worker")
    print("Then run 'python send_message.py \"<prompt>\"'")
    asyncio.run(main())
