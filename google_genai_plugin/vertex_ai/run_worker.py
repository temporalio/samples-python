"""Worker for the Vertex AI sample.

Uses ``genai.Client(vertexai=True, ...)`` with Application Default Credentials
(no API key). Run ``gcloud auth application-default login`` first, or set
``GOOGLE_APPLICATION_CREDENTIALS`` to a service-account key file.
"""

# @@@SNIPSTART python-google-genai-vertex-ai-worker
import asyncio
import os

from google import genai
from temporalio.client import Client
from temporalio.contrib.google_genai import GoogleGenAIPlugin
from temporalio.worker import Worker

from google_genai_plugin.vertex_ai.workflow import VertexAIWorkflow


async def main() -> None:
    genai_client = genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    plugin = GoogleGenAIPlugin(genai_client)

    client = await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        plugins=[plugin],
    )

    worker = Worker(
        client,
        task_queue="google-genai-vertex-ai",
        workflows=[VertexAIWorkflow],
    )
    print("Worker started. Ctrl+C to exit.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
