import uuid

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from custom_metric.worker import ExecuteActivityWorkflow

_TASK_QUEUE = "custom-metric-task-queue"

activity_counter = 0


async def test_sleep_for_days_workflow():

    @activity.defn(name="print_message")
    async def print_message_mock():
        global activity_counter
        activity_counter += 1

    async with await WorkflowEnvironment.start_time_skipping() as env:

        async with Worker(
            env.client,
            task_queue=_TASK_QUEUE,
            workflows=[ExecuteActivityWorkflow],
            activities=[print_message_mock],
        ):
            result = await env.client.execute_workflow(
                ExecuteActivityWorkflow.run,
                id=str(uuid.uuid4()),
                task_queue=_TASK_QUEUE,
            )
            assert result is None
            assert activity_counter == 2
