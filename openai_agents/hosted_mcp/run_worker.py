from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin
from temporalio.worker import Worker

from openai_agents.hosted_mcp.workflows.approval_mcp_workflow import ApprovalMCPWorkflow
from openai_agents.hosted_mcp.workflows.simple_mcp_workflow import SimpleMCPWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60)
                )
            ),
        ],
    )

    worker = Worker(
        client,
        task_queue="openai-agents-hosted-mcp-task-queue",
        workflows=[
            SimpleMCPWorkflow,
            ApprovalMCPWorkflow,
        ],
        activities=[
            # No custom activities needed for these workflows
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
