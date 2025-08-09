import asyncio
import uuid

from temporalio.client import Client

from mcp_examples.sequential_thinking.agent_workflow_nexus_client import (
    AgentWorkflowNexusClient,
)


async def main():
    client = await Client.connect("localhost:7233")
    workflow_id = f"mcp-agent-test-{uuid.uuid4().hex[:8]}"

    handle = await client.start_workflow(
        AgentWorkflowNexusClient.run,
        id=workflow_id,
        task_queue="mcp-sequential-thinking-task-queue",
    )

    print(f"Started workflow {handle.id}")
    result = await handle.result()
    print(f"Workflow completed: {result}")


if __name__ == "__main__":
    asyncio.run(main())
