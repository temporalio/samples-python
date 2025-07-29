import asyncio
import os

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.basic.workflows.local_image_workflow import LocalImageWorkflow


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Use the media file from the original example
    image_path = os.path.join(os.path.dirname(__file__), "media/image_bison.jpg")

    result = await client.execute_workflow(
        LocalImageWorkflow.run,
        args=[image_path, "What do you see in this image?"],
        id="local-image-workflow",
        task_queue="openai-agents-basic-task-queue",
    )

    print(f"Agent response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
