from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.envconfig import ClientConfig

from openai_agents.mcp.workflows.sse_workflow import SseWorkflow


async def main():
    # Create client connected to server at the given address
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(
        **config,
        plugins=[OpenAIAgentsPlugin()],
    )

    # Execute a workflow
    result = await client.execute_workflow(
        SseWorkflow.run,
        id="sse-workflow",
        task_queue="openai-agents-mcp-sse-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
