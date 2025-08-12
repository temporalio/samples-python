import asyncio
import json
from pathlib import Path

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.envconfig import ClientConfig

from openai_agents.handoffs.workflows.message_filter_workflow import (
    MessageFilterWorkflow,
)


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    # Create client connected to server at the given address
    client = await Client.connect(
        **config,
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        MessageFilterWorkflow.run,
        "Sora",
        id="message-filter-workflow",
        task_queue="openai-agents-handoffs-task-queue",
    )

    print(f"Final output: {result.final_output}")
    print("\n===Final messages===\n")

    # Print the final message history to see the effect of the message filter
    for message in result.final_messages:
        print(json.dumps(message, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
