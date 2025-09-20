from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin

from openai_agents.mcp.workflows.sequentialthinking_stateful_workflow import (
    SequentialThinkingWorkflow,
)


async def main():
    client = await Client.connect(
        "localhost:7233",
        plugins=[OpenAIAgentsPlugin()],
    )

    result = await client.execute_workflow(
        SequentialThinkingWorkflow.run,
        id="sequentialthinking-stateful-workflow",
        task_queue="openai-agents-mcp-sequential-stateful-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
