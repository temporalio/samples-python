import sys
import uuid

import pytest
import trio_asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from trio_async import activities, workflows

# Skip entire module on Python 3.14+
if sys.version_info >= (3, 14):
    pytest.skip("trio-asyncio not supported on Python 3.14+", allow_module_level=True)


async def test_workflow_with_trio(client: Client):
    @trio_asyncio.aio_as_trio
    async def inside_trio(client: Client) -> list[str]:
        # Create Trio thread executor
        with trio_asyncio.TrioExecutor(max_workers=200) as thread_executor:
            task_queue = f"tq-{uuid.uuid4()}"
            # Run worker
            async with Worker(
                client,
                task_queue=task_queue,
                activities=[
                    activities.say_hello_activity_async,
                    activities.say_hello_activity_sync,
                ],
                workflows=[workflows.SayHelloWorkflow],
                activity_executor=thread_executor,
                workflow_task_executor=thread_executor,
            ):
                # Run workflow and return result
                return await client.execute_workflow(
                    workflows.SayHelloWorkflow.run,
                    "some-user",
                    id=f"wf-{uuid.uuid4()}",
                    task_queue=task_queue,
                )

    if sys.version_info[:2] < (3, 12):
        pytest.skip("Trio support requires >= 3.12")

    result = trio_asyncio.run(inside_trio, client)

    assert result == [
        "Hello, some-user! (from asyncio)",
        "Hello, some-user! (from thread)",
    ]
