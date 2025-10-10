import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.activities.get_weather_activity import get_weather
from openai_agents.basic.workflows.tools_workflow import ToolsWorkflow


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[ToolsWorkflow],
        activity_executor=ThreadPoolExecutor(5),
        activities=[get_weather],
    ):
        result = await client.execute_workflow(
            ToolsWorkflow.run,
            "What's the weather like in New York?",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

        # Verify the result is a string response
        assert isinstance(result, str)
        assert len(result) > 0
