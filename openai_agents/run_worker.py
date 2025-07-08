from __future__ import annotations

import asyncio
import concurrent.futures
from datetime import timedelta

from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    set_open_ai_agent_temporal_overrides,
    ModelActivity,
)
from temporalio.worker import Worker
from temporalio.contrib.pydantic import pydantic_data_converter

from openai_agents.workflows.agents_as_tools_workflow import AgentsAsToolsWorkflow
from openai_agents.workflows.customer_service_workflow import CustomerServiceWorkflow
from openai_agents.workflows.get_weather_activity import get_weather
from openai_agents.workflows.hello_world_workflow import HelloWorldAgent
from openai_agents.workflows.research_bot_workflow import ResearchWorkflow
from openai_agents.workflows.tools_workflow import ToolsWorkflow


async def main():
    with set_open_ai_agent_temporal_overrides():
        # Create client connected to server at the given address
        client = await Client.connect(
            "localhost:7233",
            data_converter=pydantic_data_converter,
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
                ModelActivity().invoke_model_activity,
                get_weather,
            ],
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
