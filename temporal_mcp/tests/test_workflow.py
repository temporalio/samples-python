import asyncio
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
import pytest_asyncio
import uvicorn
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from run_worker import create_plugin
from server import create_server
from workflow import TRANSPORTS, MCPDemoResult, MCPDemoWorkflow, Transport


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def env() -> AsyncIterator[WorkflowEnvironment]:
    environment = await WorkflowEnvironment.start_local()
    yield environment
    await environment.shutdown()


@asynccontextmanager
async def http_server() -> AsyncIterator[str]:
    server = create_server()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        host="127.0.0.1",
    )
    uvicorn_server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    task = asyncio.create_task(uvicorn_server.serve(sockets=[sock]))
    try:
        for _ in range(500):
            if uvicorn_server.started:
                break
            if task.done():
                await task
            await asyncio.sleep(0.01)
        else:
            raise RuntimeError("Streamable HTTP MCP server did not start")
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        uvicorn_server.should_exit = True
        try:
            await asyncio.gather(task, return_exceptions=True)
        finally:
            sock.close()


@asynccontextmanager
async def http_url(transport: Transport) -> AsyncIterator[str]:
    if transport == "streamable-http":
        async with http_server() as url:
            yield url
    else:
        yield "http://unused.invalid/mcp"


@pytest.mark.parametrize("transport", TRANSPORTS)
async def test_workflow_through_each_transport(
    env: WorkflowEnvironment, transport: Transport
) -> None:
    task_queue = f"temporal-mcp-test-{uuid4()}"
    async with http_url(transport) as url:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[MCPDemoWorkflow],
            plugins=[create_plugin(transport, url)],
        ):
            result = await env.client.execute_workflow(
                MCPDemoWorkflow.run,
                transport,
                id=f"temporal-mcp-test-{uuid4()}",
                task_queue=task_queue,
            )

    assert result == MCPDemoResult(
        tools=["echo"],
        tool_output="durable execution",
        prompts=["greeting"],
        prompt_output="Hello, Temporal!",
        resources=["about"],
        resource_templates=["item"],
        resource_output="Temporal workflows can call MCP operations durably.",
    )
