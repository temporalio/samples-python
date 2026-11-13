import uuid
from collections import Counter
from collections.abc import AsyncGenerator

import pytest_asyncio
from temporalio.agent_framework import AgentFrameworkPlugin
from temporalio.agent_framework.testing import (
    fake_chat_client,
    function_call_response,
    text_response,
)
from temporalio.api.enums.v1 import EventType
from temporalio.client import Client, WorkflowHandle
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from run_worker import echo_mcp_client
from workflow import MCPWorkflow

INVOKE_MODEL = "agent_framework.invoke_model"
LIST_TOOLS = "temporalio.mcp.echo.list-tools"
CALL_TOOL = "temporalio.mcp.echo.call-tool"


@pytest_asyncio.fixture(scope="session")
async def env() -> AsyncGenerator[WorkflowEnvironment, None]:
    environment = await WorkflowEnvironment.start_local()
    yield environment
    await environment.shutdown()


async def count_scheduled_activities(handle: WorkflowHandle) -> Counter[str]:
    counts: Counter[str] = Counter()
    async for event in handle.fetch_history_events():
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED:
            counts[
                event.activity_task_scheduled_event_attributes.activity_type.name
            ] += 1
    return counts


async def test_mcp_tool_runs_as_activities(env: WorkflowEnvironment) -> None:
    # A scripted model: one call to the server's echo tool, then the answer.
    # The MCP server is the real echo_mcp_server.py, started over stdio by
    # the same factory the Worker uses.
    factory = fake_chat_client(
        [
            function_call_response(
                "echo", {"message": "hello from MCP"}, call_id="call-1"
            ),
            text_response("The server echoed: hello from MCP"),
        ]
    )
    plugin = AgentFrameworkPlugin(
        chat_clients={"gpt-4o-mini": factory}, mcp_clients={"echo": echo_mcp_client}
    )
    config = env.client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)
    task_queue = f"agent-framework-mcp-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MCPWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            MCPWorkflow.run,
            "Echo 'hello from MCP'.",
            id=f"agent-framework-mcp-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert result == "The server echoed: hello from MCP"
    # The listing and the call each ran as an MCP Activity, around two model calls.
    assert await count_scheduled_activities(handle) == {
        INVOKE_MODEL: 2,
        LIST_TOOLS: 1,
        CALL_TOOL: 1,
    }
    # The model saw the server's tool with the server's own schema.
    first_call, _ = factory().calls
    (echo_tool,) = first_call["options"]["tools"]
    assert echo_tool.name == "echo"
    assert echo_tool.parameters()["required"] == ["message"]
