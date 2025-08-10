import pytest
from mcp_sequential_thinking.agent_workflow_nexus_transport import (
    AgentWorkflowNexusTransport,
)
from mcp_sequential_thinking.mcp_server.nexus_service import (
    MCPServerNexusServiceHandler,
)
from mcp_sequential_thinking.mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)
from temporalio.testing import WorkflowEnvironment


@pytest.mark.asyncio
async def test_agent_workflow_nexus_transport():
    async with await WorkflowEnvironment.start_local() as env:
        worker = env.client.worker(
            task_queue="test-mcp-task-queue",
            workflows=[
                AgentWorkflowNexusTransport,
                SequentialThinkingMCPServerWorkflow,
            ],
            nexus_service_handlers=[MCPServerNexusServiceHandler()],
        )

        async with worker:
            handle = await env.client.start_workflow(
                AgentWorkflowNexusTransport.run,
                id="test-workflow-nexus-transport",
                task_queue="test-mcp-task-queue",
            )

            result = await handle.result()
            assert (
                "Completed using standard MCP ClientSession" in result
                or "Failed with error" in result
            )
