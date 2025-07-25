from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    ModelActivityParameters,
    OpenAIAgentsPlugin
)
from temporalio.worker import Worker
from temporalio.client import ClientConfig

from openai_agents.workflows.agents_as_tools_workflow import AgentsAsToolsWorkflow
from openai_agents.workflows.customer_service_workflow import CustomerServiceWorkflow
from openai_agents.workflows.get_weather_activity import get_weather
from openai_agents.workflows.hello_world_workflow import HelloWorldAgent
from openai_agents.workflows.research_bot_workflow import ResearchWorkflow
from openai_agents.workflows.tools_workflow import ToolsWorkflow


async def main():
    # Create client connected to server at the given address
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                start_to_close_timeout=timedelta(seconds=120)
                )
            ),
        ]
    )

    worker = Worker(
        client,
        task_queue="openai-agents-task-queue",
        workflows=[
            HelloWorldAgent,
            ToolsWorkflow,
            ResearchWorkflow,
            CustomerServiceWorkflow,
            AgentsAsToolsWorkflow,
        ],
        activities=[
            get_weather,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
