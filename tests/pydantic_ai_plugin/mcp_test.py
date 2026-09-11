import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.mcp.workflow import MCPInput, MCPWorkflow
from tests.pydantic_ai_plugin.helpers import with_pydantic_ai


async def test_stateless_mcp_tool(client: Client) -> None:
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-mcp-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MCPWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            MCPWorkflow.run,
            MCPInput(prompt="Find support hours."),
            id=f"pydantic-ai-mcp-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "Hours found."
