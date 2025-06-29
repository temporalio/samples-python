from __future__ import annotations

import asyncio
import concurrent.futures
from datetime import timedelta

from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.openai_agents.invoke_model_activity import ModelActivity
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)
from temporalio.contrib.openai_agents.temporal_openai_agents import (
    set_open_ai_agent_temporal_overrides,
)
from temporalio.worker import Worker

from openai_agents.workflows.agents_as_tools_workflow import AgentsAsToolsWorkflow
from openai_agents.workflows.customer_service_workflow import CustomerServiceWorkflow
from openai_agents.workflows.get_weather_activity import get_weather
from openai_agents.workflows.hello_world_workflow import HelloWorldAgent
from openai_agents.workflows.research_bot_workflow import ResearchWorkflow
from openai_agents.workflows.tools_workflow import ToolsWorkflow


async def main():
    with set_open_ai_agent_temporal_overrides(
        start_to_close_timeout=timedelta(seconds=60),
    ):
        # Create client connected to server at the given address
        client = await Client.connect(
            "localhost:7233",
            data_converter=open_ai_data_converter,
        )

        model_activity = ModelActivity(model_provider=None)
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
                model_activity.invoke_model_activity,
                get_weather,
            ],
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
