import asyncio
import io
import logging
import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from hello.hello_change_log_level import LOG_MESSAGE, GreetingWorkflow


async def test_workflow_with_log_capture(client: Client):

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    task_queue = f"tq-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[GreetingWorkflow],
    ):
        handle = await client.start_workflow(
            GreetingWorkflow.run,
            id=f"wf-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        await asyncio.sleep(
            0.2
        )  # small wait to ensure the workflow has started, failed, and logged
        await handle.terminate()

    logger.removeHandler(handler)
    handler.flush()

    logs = log_stream.getvalue()
    assert LOG_MESSAGE in logs
