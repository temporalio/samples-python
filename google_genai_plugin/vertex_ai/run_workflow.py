"""Start the Vertex AI workflow."""

# @@@SNIPSTART python-google-genai-vertex-ai-run-workflow
import asyncio
import os

from temporalio.client import Client

from google_genai_plugin.vertex_ai.workflow import VertexAIWorkflow


async def main() -> None:
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))

    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    result = await client.execute_workflow(
        VertexAIWorkflow.run,
        args=["Write a haiku about durable execution.", project, location],
        id="google-genai-vertex-ai",
        task_queue="google-genai-vertex-ai",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
# @@@SNIPEND
