from datetime import datetime, timezone
from typing import Optional

from temporalio import workflow

from updatable_timer.updatable_timer_lib import UpdatableTimer


@workflow.defn
class Workflow:
    def __init__(self):
        self.timer: Optional[UpdatableTimer] = None

    @workflow.run
    async def run(self, wake_up_time: float):
        self.timer = UpdatableTimer(
            datetime.fromtimestamp(wake_up_time, tz=timezone.utc)
        )
        await self.timer.sleep()

    @workflow.signal
    async def update_wake_up_time(self, wake_up_time: float):
        # Deals with situation when the signal method is called before the run method.
        # This happens when a workflow task is executed after a signal is received
        # or when a workflow is started using the signal-with-start.
        await workflow.wait_condition(lambda: self.timer is not None)
        assert self.timer is not None  # for mypy
        self.timer.update_wake_up_time(
            datetime.fromtimestamp(wake_up_time, tz=timezone.utc)
        )

    @workflow.query
    def get_wake_up_time(self):
        assert self.timer is not None  # for mypy
        return self.timer.get_wake_up_time()
