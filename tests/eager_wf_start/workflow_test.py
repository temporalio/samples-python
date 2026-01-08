import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from eager_wf_start.activities import greeting
from eager_wf_start.workflows import EagerWorkflow


async def test_eager_wf_start(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[EagerWorkflow],
        activities=[greeting],
    ):
        handle = await client.start_workflow(
            EagerWorkflow.run,
            "Temporal",
            id=f"workflow-{uuid.uuid4()}",
            task_queue=task_queue_name,
            request_eager_start=True,
        )
        print("HANDLE", handle.__temporal_eagerly_started)
        assert handle.__temporal_eagerly_started
        result = await handle.result()
        assert result == "Hello Temporal!"
