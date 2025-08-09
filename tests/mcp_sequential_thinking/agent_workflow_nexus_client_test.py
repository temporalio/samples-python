import pytest
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from mcp_sequential_thinking.agent_workflow_nexus_client import AgentWorkflowNexusClient
from mcp_sequential_thinking.mcp_server.nexus_service import (
    MCPServerNexusServiceHandler,
)
from mcp_sequential_thinking.mcp_server.workflow import (
    SequentialThinkingMCPServerWorkflow,
)

from .helpers import create_nexus_endpoint, delete_nexus_endpoint


@pytest.mark.asyncio
async def test_agent_workflow_nexus_client(client: Client, env: WorkflowEnvironment):
    if env.supports_time_skipping:
        pytest.skip("Nexus tests don't work under the Java test server")

    task_queue = "test-mcp-task-queue"
    nexus_endpoint = "mcp-sequential-thinking-nexus-endpoint"

    create_response = await create_nexus_endpoint(
        name=nexus_endpoint,
        task_queue=task_queue,
        client=client,
    )

    try:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[AgentWorkflowNexusClient, SequentialThinkingMCPServerWorkflow],
            nexus_service_handlers=[MCPServerNexusServiceHandler()],
        ):
            handle = await client.start_workflow(
                AgentWorkflowNexusClient.run,
                id="test-workflow-nexus-client",
                task_queue=task_queue,
            )

            result = await handle.result()
            assert "Completed MCP interaction" in result
            assert "thoughtHistoryLength" in result

    finally:
        await delete_nexus_endpoint(
            id=create_response.endpoint.id,
            version=create_response.endpoint.version,
            client=client,
        )
