from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.mcp.workflows.memory_research_scratchpad_workflow import (
    MemoryResearchScratchpadWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[OpenAIAgentsPlugin()],
    )

    result = await client.execute_workflow(
        MemoryResearchScratchpadWorkflow.run,
        id="memory-research-scratchpad-workflow",
        task_queue="openai-agents-mcp-memory-task-queue",
    )

    print(f"Result:\n{result}")


if __name__ == "__main__":
    asyncio.run(main())
