from __future__ import annotations

import asyncio
import shutil
from datetime import timedelta

from agents.mcp import MCPServerSse
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    StatelessMCPServerProvider,
)
import logging
from temporalio.worker import Worker

from openai_agents.mcp.workflows.sse_stateless_workflow import SseWorkflow


async def main():
    logging.basicConfig(level=logging.DEBUG)
    
    print("Setting up worker...\n")

    try:
        sse_server_provider = StatelessMCPServerProvider(
            lambda: MCPServerSse(
                name="SseServer",
                params={
                    "url": "http://localhost:8000/sse",
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
                    mcp_servers=[sse_server_provider],
                ),
            ],
        )

        worker = Worker(
            client,
            task_queue="openai-agents-mcp-stateless-task-queue",
            workflows=[
                SseWorkflow,
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