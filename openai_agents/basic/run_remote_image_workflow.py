import asyncio
from pathlib import Path

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.envconfig import ClientConfig

from openai_agents.basic.workflows.remote_image_workflow import RemoteImageWorkflow


async def main():
    # Get repo root - 2 levels deep from root

    repo_root = Path(__file__).resolve().parent.parent.parent

    config_file = repo_root / "temporal.toml"

    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    config["plugins"] = [
        OpenAIAgentsPlugin(),
    ]
    
    client = await Client.connect(**config)

    # Use the URL from the original example
    image_url = (
        "https://upload.wikimedia.org/wikipedia/commons/0/0c/GoldenGateBridge-001.jpg"
    )

    result = await client.execute_workflow(
        RemoteImageWorkflow.run,
        args=[image_url, "What do you see in this image?"],
        id="remote-image-workflow",
        task_queue="openai-agents-basic-task-queue",
    )

    print(f"Agent response: {result}")


if __name__ == "__main__":
    asyncio.run(main())
