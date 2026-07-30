from datetime import datetime, timezone
from typing import Optional

from temporalio import workflow

from updatable_timer.updatable_timer_lib import UpdatableTimer


@workflow.defn
class Workflow:
    @workflow.init
    def __init__(self, wake_up_time: float) -> None:
        self.timer = UpdatableTimer(
            datetime.fromtimestamp(wake_up_time, tz=timezone.utc)
        )

    @workflow.run
    async def run(self, wake_up_time: float):
        await self.timer.sleep()

    @workflow.signal
    async def update_wake_up_time(self, wake_up_time: float) -> None:
        workflow.logger.info(f"update_wake_up_time: {wake_up_time}")

        self.timer.update_wake_up_time(
            datetime.fromtimestamp(wake_up_time, tz=timezone.utc)
        )

    @workflow.query
    def get_wake_up_time(self) -> float:
        workflow.logger.info(f"get_wake_up_time")
        return float(self.timer.get_wake_up_time().timestamp())
