import asyncio
import uuid

from temporalio.client import Client

from mcp_sequential_thinking.agent_workflow_nexus_transport import (
    AgentWorkflowNexusTransport,
)


async def main():
    client = await Client.connect("localhost:7233")
    workflow_id = f"mcp-transport-test-{uuid.uuid4().hex[:8]}"

    handle = await client.start_workflow(
        AgentWorkflowNexusTransport.run,
        id=workflow_id,
        task_queue="mcp-sequential-thinking-task-queue",
    )

    print(f"Started transport workflow {handle.id}")
    result = await handle.result()
    print(f"Workflow completed: {result}")


if __name__ == "__main__":
    asyncio.run(main())
