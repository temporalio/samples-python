import uuid

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from custom_metric.worker import StartTwoActivitiesWorkflow

_TASK_QUEUE = "custom-metric-task-queue"

activity_counter = 0


async def test_custom_metric_workflow(client: Client):
    @activity.defn(name="print_and_sleep")
    async def print_message_mock():
        global activity_counter
        activity_counter += 1

    async with Worker(
        client,
        task_queue=_TASK_QUEUE,
        workflows=[StartTwoActivitiesWorkflow],
        activities=[print_message_mock],
    ):
        result = await client.execute_workflow(
            StartTwoActivitiesWorkflow.run,
            id=str(uuid.uuid4()),
            task_queue=_TASK_QUEUE,
        )
        assert result is None
        assert activity_counter == 2
