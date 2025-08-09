"""
Start the agent workflow to test the MCP integration.
"""

import asyncio
import uuid

from temporalio.client import Client

from mcp_sequential_thinking.agent_workflow import AgentWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    # Start the agent workflow with unique ID
    workflow_id = f"mcp-agent-test-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        AgentWorkflow.run,
        id=workflow_id,
        task_queue="mcp-sequential-thinking-task-queue",
    )

    print(f"Started workflow {handle.id}")

    # Wait for completion
    result = await handle.result()
    print(f"Workflow completed: {result}")


if __name__ == "__main__":
    asyncio.run(main())
