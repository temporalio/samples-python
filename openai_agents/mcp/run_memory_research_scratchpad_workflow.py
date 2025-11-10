from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin
from temporalio.envconfig import ClientConfig

from openai_agents.mcp.workflows.memory_research_scratchpad_workflow import (
    MemoryResearchScratchpadWorkflow,
)


async def main():
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(
        **config,         
        plugins=[
            OpenAIAgentsPlugin(),
        ],
    )

    result = await client.execute_workflow(
        MemoryResearchScratchpadWorkflow.run,
        id="memory-research-scratchpad-workflow",
        task_queue="openai-agents-mcp-memory-task-queue",
    )

    print(f"Result:\n{result}")


if __name__ == "__main__":
    asyncio.run(main())
