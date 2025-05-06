from __future__ import annotations

import asyncio
import concurrent.futures

from temporalio.client import Client
from temporalio.worker import Worker

from agents import TResponseInputItem
from openai_agents.adapters.model_activity import invoke_open_ai_model
from openai_agents.workflows.agents_as_tools_workflow import AgentsAsToolsWorkflow
from openai_agents.workflows.get_weather_activity import get_weather
from openai_agents.workflows.customer_service_workflow import CustomerServiceWorkflow
from openai_agents.adapters.open_ai_converter import open_ai_data_converter
from openai_agents.workflows.research_bot_workflow import ResearchWorkflow
from openai_agents.workflows.tools_workflow import ToolsWorkflow
from openai_agents.workflows.hello_world_workflow import HelloWorldAgent

async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233",
                                  data_converter=open_ai_data_converter)

    item = TResponseInputItem
    # Run the worker
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue="my-task-queue",
            workflows=[HelloWorldAgent, ToolsWorkflow, ResearchWorkflow, CustomerServiceWorkflow,
                       AgentsAsToolsWorkflow],
            activities=[invoke_open_ai_model, get_weather],
            activity_executor=activity_executor,
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
