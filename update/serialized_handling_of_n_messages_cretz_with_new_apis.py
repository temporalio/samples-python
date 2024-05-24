from collections import deque
from datetime import timedelta
from typing import Optional

from temporalio import workflow

# !!!
# This version requires update to complete with result and won't CAN until after
# everything is done
# !!!


class UpdateTask:
    def __init__(self, arg: str, update_id: str) -> None:
        self.arg = arg
        self.update_id: str
        self.result: Optional[str] = None


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
        task = UpdateTask(arg, update_id=workflow.current_update_id())
        self.queue.append(task)
        await workflow.wait_condition(lambda: task.result is not None)
        return task.result
        
    async def process_task(self, task: UpdateTask) -> None:
        # execute_activity(...)
        await workflow.wait_condition(lambda: workflow.update_completed(task.update_id))
