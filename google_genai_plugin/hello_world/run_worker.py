"""Worker for the hello world sample."""

# @@@SNIPSTART python-google-genai-hello-world-worker
import asyncio
import os

from google import genai
from temporalio.client import Client
from temporalio.contrib.google_genai import GoogleGenAIPlugin
from temporalio.worker import Worker

from google_genai_plugin.hello_world.workflow import HelloWorldWorkflow


async def main() -> None:
    # The real genai.Client (with credentials) lives only on the worker.
    genai_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    plugin = GoogleGenAIPlugin(genai_client)

    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="google-genai-hello-world",
        workflows=[HelloWorldWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
