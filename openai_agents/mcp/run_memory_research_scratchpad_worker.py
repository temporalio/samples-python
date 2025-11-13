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
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from openai_agents.mcp.workflows.memory_research_scratchpad_workflow import (
    MemoryResearchScratchpadWorkflow,
)


async def main():
    logging.basicConfig(level=logging.INFO)

    memory_server_provider = StatefulMCPServerProvider(
        "MemoryServer",
        lambda _: MCPServerStdio(
            name="MemoryServer",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
            },
        ),
    )

    # Create client connected to server at the given address
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(
        **config,
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                ),
                mcp_server_providers=[memory_server_provider],
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-mcp-memory-task-queue",
        workflows=[
            MemoryResearchScratchpadWorkflow,
        ],
        activities=[],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
