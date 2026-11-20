from __future__ import annotations

import asyncio
from typing import Any

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.openai_agents import OpenAIAgentsPlugin

from openai_agents.mcp.workflows.sse_workflow import SseWorkflow


async def main():
    # Create client connected to server at the given address
    config: dict[str, Any] = dict(ClientConfig.load_client_connect_config())
    config.setdefault("target_host", "localhost:7233")
    config["plugins"] = [*config.get("plugins", []), OpenAIAgentsPlugin()]
    client = await Client.connect(**config)

    # Execute a workflow
    result = await client.execute_workflow(
        SseWorkflow.run,
        id="sse-workflow",
        task_queue="openai-agents-mcp-sse-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
