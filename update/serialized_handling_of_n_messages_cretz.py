from collections import deque
from datetime import timedelta
from typing import Optional

from temporalio import workflow

# !!!
# This version requires update to complete with result and won't CAN until after
# everything is done
# !!!


class UpdateTask:
    def __init__(self, arg: str) -> None:
        self.arg = arg
        self.result: Optional[str] = None
        self.returned = False


@workflow.defn
class MessageProcessor:
    def __init__(self) -> None:
        self.queue: deque[UpdateTask] = deque()

    @workflow.run
    async def run(self) -> None:
        while not workflow.info().is_continue_as_new_suggested() or len(self.queue) > 0:
            await workflow.wait_condition(lambda: len(self.queue) > 0)
            await self.process_task(self.queue.popleft())
        workflow.continue_as_new()

    @workflow.update
    async def do_task(self, arg: str) -> str:
        # Add task and wait on result
        task = UpdateTask(arg)
        try:
            self.queue.append(task)
            await workflow.wait_condition(lambda: task.result is not None)
            assert task.result
            return task.result
        finally:
            task.returned = True

    async def process_task(self, task: UpdateTask) -> None:
        task.result = await workflow.execute_activity(
            "some_activity", task.arg, start_to_close_timeout=timedelta(seconds=10)
        )
        await workflow.wait_condition(lambda: task.returned)
