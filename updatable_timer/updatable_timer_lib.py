import asyncio
from datetime import datetime, timedelta

from temporalio import workflow


class UpdatableTimer:
    def __init__(self, wake_up_time: datetime) -> None:
        self.wake_up_time = wake_up_time
        self.wake_up_time_updated = False

    async def sleep(self) -> None:
        workflow.logger.info(f"sleep_until: {self.wake_up_time}")
        while True:
            now = workflow.now()

            sleep_interval = self.wake_up_time - now
            if sleep_interval <= timedelta(0):
                break
            workflow.logger.info(f"Going to sleep for {sleep_interval}")

            try:
                self.wake_up_time_updated = False
                await workflow.wait_condition(
                    lambda: self.wake_up_time_updated,
                    timeout=sleep_interval,
                )
            except asyncio.TimeoutError:
                # checks condition at the beginning of the loop
                continue
        workflow.logger.info(f"sleep_until completed")

    def update_wake_up_time(self, wake_up_time: datetime) -> None:
        workflow.logger.info(f"update_wake_up_time:  {wake_up_time}")
        self.wake_up_time = wake_up_time
        self.wake_up_time_updated = True

    def get_wake_up_time(self) -> datetime:
        return self.wake_up_time
