from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from agents.mcp import MCPServerStdio
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    StatefulMCPServerProvider,
)
from temporalio.worker import Worker

from openai_agents.mcp.workflows.sequentialthinking_stateful_workflow import (
    SequentialThinkingWorkflow,
)


async def main():
    logging.basicConfig(level=logging.INFO)

    sequential_server_provider = StatefulMCPServerProvider(
        lambda: MCPServerStdio(
            name="SequentialThinkingServer",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
            },
        )
    )

    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                mcp_servers=[sequential_server_provider],
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-mcp-sequential-stateful-task-queue",
        workflows=[
            SequentialThinkingWorkflow,
        ],
        activities=[],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
