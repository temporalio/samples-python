import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.signals import TASK_QUEUE
from workflow_pause.signals.workflow import SignalPauseWorkflow


async def test_signals_collected_then_done(client: Client, env: WorkflowEnvironment):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[SignalPauseWorkflow]):
        handle = await client.start_workflow(
            SignalPauseWorkflow.run,
            id=f"signals-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        await handle.signal(SignalPauseWorkflow.add_message, "hello")
        await handle.signal(SignalPauseWorkflow.add_message, "world")
        await handle.signal(SignalPauseWorkflow.add_message, "done")
        result = await handle.result()
        assert result == ["hello", "world"]
