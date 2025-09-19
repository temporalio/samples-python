from __future__ import annotations

import asyncio
import shutil
from datetime import timedelta

from agents.mcp import MCPServerStreamableHttp
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    StatelessMCPServerProvider,
)
import logging
from temporalio.worker import Worker

from openai_agents.mcp.workflows.streamable_http_stateless_workflow import StreamableHttpWorkflow


async def main():
    logging.basicConfig(level=logging.DEBUG)
    
    print("Setting up worker...\n")

    try:
        streamable_http_server_provider = StatelessMCPServerProvider(
            lambda: MCPServerStreamableHttp(
                name="StreamableHttpServer",
                params={
                    "url": "http://localhost:8000/mcp",
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
                    mcp_servers=[streamable_http_server_provider],
                ),
            ],
        )

        worker = Worker(
            client,
            task_queue="openai-agents-mcp-stateless-task-queue",
            workflows=[
                StreamableHttpWorkflow,
            ],
            activities=[
                # No custom activities needed for these workflows
            ],
        )
        logging.debug("STARTED WORKER")
        await worker.run()
    except Exception as e:
        print(f"Worker failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())