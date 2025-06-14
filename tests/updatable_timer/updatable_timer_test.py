import datetime
import logging
import math
import uuid

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from updatable_timer.workflow import Workflow


async def test_updatable_timer_workflow(client: Client):
    logging.basicConfig(level=logging.DEBUG)

    task_queue_name = str(uuid.uuid4())
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=task_queue_name, workflows=[Workflow]):
            in_a_day = float(
                (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp()
            )
            in_an_hour = float(
                (datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()
            )
            handle = await env.client.start_workflow(
                Workflow.run, in_a_day, id=str(uuid.uuid4()), task_queue=task_queue_name
            )
            wake_up_time1 = await handle.query(Workflow.get_wake_up_time)
            assert math.isclose(wake_up_time1, in_a_day)
            await handle.signal(Workflow.update_wake_up_time, in_an_hour)
            wake_up_time2 = await handle.query(Workflow.get_wake_up_time)
            assert math.isclose(wake_up_time2, in_an_hour)
            await handle.result()
