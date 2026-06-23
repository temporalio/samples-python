from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import (
    GoogleAdkPlugin,
    TemporalMcpToolSetProvider,
)
from temporalio.worker import Worker

from google_adk_agents.mcp.toolsets import echo_toolset
from google_adk_agents.mcp.workflows.echo_workflow import EchoMcpWorkflow


async def main():
    # The provider adds the echo-list-tools and echo-call-tool activities. Same
    # as the other samples: build the plugin once and give the same instance to
    # the client and the worker.
    plugin = GoogleAdkPlugin(
        toolset_providers=[TemporalMcpToolSetProvider("echo", echo_toolset)]
    )

    client = await Client.connect("localhost:7233", plugins=[plugin])

    worker = Worker(
        client,
        task_queue="google-adk-agents-mcp",
        workflows=[EchoMcpWorkflow],
        plugins=[plugin],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
