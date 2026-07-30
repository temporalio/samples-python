import asyncio
import base64
import os
import subprocess
import sys
import tempfile

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.tools.workflows.image_generator_workflow import (
    ImageGeneratorWorkflow,
)


def open_file(path: str) -> None:
    if sys.platform.startswith("darwin"):
        subprocess.run(["open", path], check=False)  # macOS
    elif os.name == "nt":  # Windows
        os.startfile(path)  # type: ignore
    elif os.name == "posix":
        subprocess.run(["xdg-open", path], check=False)  # Linux/Unix
    else:
        print(f"Don't know how to open files on this platform: {sys.platform}")


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        ImageGeneratorWorkflow.run,
        "Create an image of a frog eating a pizza, comic book style.",
        id="image-generator-workflow",
        task_queue="openai-agents-tools-task-queue",
    )

    print(f"Text result: {result.final_output}")

    if result.image_data:
        # Save and open the image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(base64.b64decode(result.image_data))
            temp_path = tmp.name

        print(f"Image saved to: {temp_path}")
        # Open the image
        open_file(temp_path)
    else:
        print("No image data found in result")


if __name__ == "__main__":
    asyncio.run(main())
