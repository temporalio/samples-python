from __future__ import annotations

import asyncio

from temporalio.client import Client

from openai_agents.mcp.workflows.prompt_server_stateless_workflow import (
    PromptServerWorkflow,
)


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Execute a workflow
    result = await client.execute_workflow(
        PromptServerWorkflow.run,
        id="prompt-server-workflow",
        task_queue="openai-agents-mcp-stateless-task-queue",
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
