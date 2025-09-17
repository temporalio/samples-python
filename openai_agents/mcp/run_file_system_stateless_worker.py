from __future__ import annotations

import asyncio
import os
from datetime import timedelta

from agents.mcp import MCPServerStdio
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    StatelessMCPServer,
)
from temporalio.worker import Worker

from openai_agents.mcp.workflows.file_system_stateless_workflow import (
    FileSystemWorkflow,
)


async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(current_dir, "sample_files")

    file_system_server = StatelessMCPServer(
        MCPServerStdio(
            name="FileSystemServer",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", samples_dir],
            },
        )
    )

    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                mcp_servers=[file_system_server],
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-mcp-stateless-task-queue",
        workflows=[
            FileSystemWorkflow,
        ],
        activities=[
            # No custom activities needed for these workflows
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
