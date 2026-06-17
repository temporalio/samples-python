from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.contrib.google_adk_agents import (
    GoogleAdkPlugin,
    TemporalMcpToolSetProvider,
)
from temporalio.worker import Worker

from google_adk_agents.mcp.toolsets import filesystem_toolset
from google_adk_agents.mcp.workflows.filesystem_workflow import FilesystemMcpWorkflow


async def main():
    # The provider contributes the filesystem-list-tools / filesystem-call-tool
    # activities. Construct the plugin once and share the same instance between
    # the client and the worker.
    plugin = GoogleAdkPlugin(
        toolset_providers=[TemporalMcpToolSetProvider("filesystem", filesystem_toolset)]
    )

    client = await Client.connect("localhost:7233", plugins=[plugin])

    worker = Worker(
        client,
        task_queue="google-adk-agents-mcp",
        workflows=[FilesystemMcpWorkflow],
        plugins=[plugin],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
