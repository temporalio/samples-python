import uuid
import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from hello.hello_change_log_level import GreetingWorkflow


async def test_workflow_with_changed_log_level(client: Client, caplog):

    task_queue = f"tq-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[GreetingWorkflow],
    ):
        with caplog.at_level(logging.ERROR):
            handle = await client.start_workflow(
                GreetingWorkflow.run,
                id=f"wf-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            await asyncio.sleep(.1)
            handle.terminate()

    assert any("log level" in m for m in caplog.messages)
    assert True
