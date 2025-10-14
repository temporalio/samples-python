import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from temporalio.client import Client
from temporalio.worker import Worker

from openai_agents.basic.workflows.remote_image_workflow import RemoteImageWorkflow


# TODO(@donald-pinckney): debug this test
async def test_execute_workflow_default_question(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[RemoteImageWorkflow],
        activity_executor=ThreadPoolExecutor(5),
        # No external activities needed - uses remote URL directly
    ):
        # Using a reliable test image URL
        test_image_url = "https://upload.wikimedia.org/wikipedia/commons/0/0c/GoldenGateBridge-001.jpg"

        result = await client.execute_workflow(
            RemoteImageWorkflow.run,
            test_image_url,
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

        # Verify the result is a string response
        assert isinstance(result, str)
        assert len(result) > 0


# TODO(@donald-pinckney): debug this test
async def test_execute_workflow_custom_question(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[RemoteImageWorkflow],
        activity_executor=ThreadPoolExecutor(5),
        # No external activities needed - uses remote URL directly
    ):
        # Using a reliable test image URL
        test_image_url = "https://upload.wikimedia.org/wikipedia/commons/0/0c/GoldenGateBridge-001.jpg"
        custom_question = "What do you see in this image?"

        result = await client.execute_workflow(
            RemoteImageWorkflow.run,
            args=[test_image_url, custom_question],
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )

        # Verify the result is a string response
        assert isinstance(result, str)
        assert len(result) > 0
