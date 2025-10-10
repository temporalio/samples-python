import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.activities.image_activities import read_image_as_base64
from openai_agents.basic.workflows.local_image_workflow import LocalImageWorkflow


async def test_execute_workflow_default_question(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[LocalImageWorkflow],
        activity_executor=ThreadPoolExecutor(5),
        activities=[read_image_as_base64],
    ):
        result = await client.execute_workflow(
            LocalImageWorkflow.run,
            "openai_agents/basic/media/image_bison.jpg",  # Path to test image
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

        # Verify the result is a string response
        assert isinstance(result, str)
        assert len(result) > 0


async def test_execute_workflow_custom_question(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[LocalImageWorkflow],
        activity_executor=ThreadPoolExecutor(5),
        activities=[read_image_as_base64],
    ):
        custom_question = "What animals do you see in this image?"
        result = await client.execute_workflow(
            LocalImageWorkflow.run,
            args=["openai_agents/basic/media/image_bison.jpg", custom_question],
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

        # Verify the result is a string response
        assert isinstance(result, str)
        assert len(result) > 0
