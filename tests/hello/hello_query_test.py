import uuid

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from hello.hello_query import GreetingWorkflow


async def test_query_workflow():
    task_queue_name = str(uuid.uuid4())
    # start manual time skipping
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client, task_queue=task_queue_name, workflows=[GreetingWorkflow]
        ):
            handle = await env.client.start_workflow(
                GreetingWorkflow.run,
                "World",
                id=str(uuid.uuid4()),
                task_queue=task_queue_name,
            )

            assert "Hello, World!" == await handle.query(GreetingWorkflow.greeting)
            # manually skip 3 seconds. This will allow the workflow execution to move forward
            await env.sleep(3)
            assert "Goodbye, World!" == await handle.query(GreetingWorkflow.greeting)
