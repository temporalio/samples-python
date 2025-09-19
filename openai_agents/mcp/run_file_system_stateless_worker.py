from __future__ import annotations

import asyncio
import os
from datetime import timedelta
import uuid

from agents.mcp import MCPServerStdio
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    StatelessMCPServerProvider,
)
from temporalio.worker import Worker

from openai_agents.mcp.workflows.file_system_stateless_workflow import (
    FileSystemWorkflow,
)


async def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(current_dir, "sample_files")

    # TODO: StatelessMCPServer will switch to StatelessMCPServerProvider instead
    file_system_server = StatelessMCPServerProvider(
        lambda: MCPServerStdio(
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
        task_queue=f"openai-agents-mcp-stateless-task-queue-{uuid.uuid4()}",
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
