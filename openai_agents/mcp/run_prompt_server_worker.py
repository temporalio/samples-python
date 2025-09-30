from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from agents.mcp import MCPServerStreamableHttp
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin,
    StatelessMCPServerProvider,
)
from temporalio.worker import Worker

from openai_agents.mcp.workflows.prompt_server_workflow import PromptServerWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    print("Setting up worker...\n")

    try:
        prompt_server_provider = StatelessMCPServerProvider(
            lambda: MCPServerStreamableHttp(
                name="PromptServer",
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
                        start_to_close_timeout=timedelta(seconds=120)
                    ),
                    mcp_server_providers=[prompt_server_provider],
                ),
            ],
        )

        worker = Worker(
            client,
            task_queue="openai-agents-mcp-prompt-task-queue",
            workflows=[
                PromptServerWorkflow,
            ],
            activities=[
                # No custom activities needed for these workflows
            ],
        )
        await worker.run()
    except Exception as e:
        print(f"Worker failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
