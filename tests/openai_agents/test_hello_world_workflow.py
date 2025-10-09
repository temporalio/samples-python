import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.activities.get_weather_activity import get_weather
from openai_agents.basic.activities.image_activities import read_image_as_base64
from openai_agents.basic.activities.math_activities import (
    multiply_by_two,
    random_number,
)
from openai_agents.basic.workflows.hello_world_workflow import HelloWorldAgent


@pytest.mark.fixt_data(42)
async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[HelloWorldAgent],
        activity_executor=ThreadPoolExecutor(5),
        activities=[
            get_weather,
            multiply_by_two,
            random_number,
            read_image_as_base64,
        ],
    ):
        await client.execute_workflow(
            HelloWorldAgent.run,
            "Write a recursive haiku about recursive haikus.",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )
