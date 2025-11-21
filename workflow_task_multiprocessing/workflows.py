from datetime import timedelta
import os

from temporalio import workflow

from workflow_task_multiprocessing import ACTIVITY_TASK_QUEUE
from workflow_task_multiprocessing.activities import echo_pid_activity


@workflow.defn
class ParallelizedWorkflow:
    @workflow.run
    async def run(self, input: str) -> str:
        pid = os.getpid()
        activity_result = await workflow.execute_activity(
            echo_pid_activity,
            f"wf-starting-pid:{pid}",
            task_queue=ACTIVITY_TASK_QUEUE,
            start_to_close_timeout=timedelta(seconds=10),
        )

        return f"{activity_result} | wf-ending-pid:{pid}"
