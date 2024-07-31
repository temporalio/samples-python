import asyncio
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from temporalio import workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

CT_TIMEZONE_OFFSET = timedelta(hours=-6)  # CT is UTC-6
WORKING_HOURS_START = time(9, 0)  # 9:00 AM CT
WORKING_HOURS_END = time(20, 0)  # 5:00 PM CT
ESTIMATED_CHECK_IN_PROCESS_TIME = 60 * 5  # 5 minutes


class CheckInStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    PENDING = "pending"
    INCOMPLETE = "incomplete"
    ANOMALOUS = "anomalous"


class UserState(Enum):
    NORMAL = "normal"
    INJURED = "injured"
    VACATION = "vacation"


@dataclass
class UserTrainerIds:
    user_id: Optional[str]
    trainer_id: Optional[str]
    temporal_client: Optional[str] = None


@dataclass
class WorkflowState:
    user_state: str
    check_in_state: str
    progress_state: str
    last_check_in_date: Optional[str]
    next_check_in_date: Optional[str]


@workflow.defn
class ScheduleCheckInWorkflow:
    def __init__(self) -> None:
        self._temporal_client = None
        self.user_id = None
        self.trainer_id = None
        self.delay_hours = 0
        self.manual_check_in_triggered = False
        self.last_check_in_date = None
        self.plan_status_check_interval = timedelta(minutes=10).total_seconds()
        self.plan_status_check_active = False

        self.user_state = UserState.NORMAL.value
        self.state = CheckInStatus.IDLE
        self.progress = CheckInStatus.IDLE.value
        self.user_responded = False
        self.trigger_immediate_check_in = False
        self.last_injured_check_in_date = None

    @workflow.run
    async def run(self, check_in_user: UserTrainerIds) -> None:
        self.user_id = check_in_user.user_id
        self.trainer_id = check_in_user.trainer_id

        while True:
            await workflow.wait_condition(lambda: True)
            current_time = workflow.now()
            await self.handle_normal_state(check_in_user, current_time)

    async def handle_normal_state(
        self, check_in_user: UserTrainerIds, current_time: datetime
    ):
        print("handle_normal_state")
        check_in_date = self.calculate_next_check_in_date(current_time)
        check_in_date_utc = check_in_date.replace(tzinfo=timezone.utc)

        while current_time < check_in_date_utc:
            duration_until_check_in = (check_in_date_utc - current_time).total_seconds()

            try:
                condition_met = await workflow.wait_condition(
                    lambda: (
                        self.manual_check_in_triggered
                        or self.delay_hours > 0
                        or self.trigger_immediate_check_in
                        or self.user_state != UserState.NORMAL.value
                    ),
                    timeout=duration_until_check_in,
                )
                if condition_met:
                    break  # Condition was met, exit the waiting loop
            except asyncio.TimeoutError:
                # Time for check-in has arrived
                pass

            current_time = workflow.now()
            await asyncio.sleep(0)

        if self.user_state != UserState.NORMAL.value:
            return  # Exit if state has changed

        if self.trigger_immediate_check_in:
            self.trigger_immediate_check_in = False
            await self._process_check_in(check_in_user)
            self.last_check_in_date = workflow.now()
            return

        if self.manual_check_in_triggered:
            self.last_check_in_date = workflow.now()
            self.manual_check_in_triggered = False
            return

        if self.delay_hours > 0:
            await asyncio.sleep(timedelta(hours=self.delay_hours).total_seconds())
            self.delay_hours = 0

        # Check message queue status
        while True:
            check_in_user.temporal_client = self._temporal_client
            queue_empty = await workflow.execute_activity(
                "check_message_queue_status",
                check_in_user,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            if not queue_empty:
                await asyncio.sleep(timedelta(minutes=5).total_seconds())
                continue

            break

        # Process check-in
        self.state = CheckInStatus.PROCESSING
        check_in_result = await workflow.execute_activity(
            "process_check_in",
            check_in_user,
            schedule_to_close_timeout=timedelta(
                seconds=ESTIMATED_CHECK_IN_PROCESS_TIME
            ),
            retry_policy=RetryPolicy(
                maximum_attempts=2, non_retryable_error_types=["ValueError", "KeyError"]
            ),
        )
        self.state = CheckInStatus.IDLE

        # Update progress based on check-in result
        if not check_in_result["plan_completed"]:
            if check_in_result["state"] == "wait":
                self.progress = CheckInStatus.PENDING.value
            elif check_in_result["state"] in ["missing_data"]:
                self.progress = CheckInStatus.INCOMPLETE.value
            elif check_in_result["state"] in ["anomalies"]:
                self.progress = CheckInStatus.ANOMALOUS.value

        self.last_check_in_date = workflow.now()

        # Check plan status periodically if needed
        if not check_in_result["plan_completed"] and self.plan_status_check_active:
            await self.check_plan_status_periodically()

        # Reset plan status check after it's done
        self.plan_status_check_active = False

    @workflow.signal
    async def set_user_state(self, state: str):
        print("set_user_state")
        self.user_state = state

    async def check_plan_status_periodically(self) -> None:
        print("check_plan_status_periodically")
        while self.plan_status_check_active:
            plan_completed = await workflow.execute_activity(
                "check_plan_status",
                self.user_id,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            if plan_completed:
                break

            await asyncio.sleep(self.plan_status_check_interval)

    async def _process_check_in(self, check_in_user: UserTrainerIds):
        print("_process_check_in")
        self.state = CheckInStatus.PROCESSING
        result = await workflow.execute_activity(
            "process_check_in",
            check_in_user,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=2, non_retryable_error_types=["ValueError", "KeyError"]
            ),
        )
        self.state = CheckInStatus.IDLE

        self.progress = result["state"]

        if result["state"] in [
            CheckInStatus.INCOMPLETE.value,
            CheckInStatus.ANOMALOUS.value,
        ]:
            await self.wait_for_user_response()

    async def wait_for_user_response(self):
        print("wait_for_user_response")
        while self.progress in [
            CheckInStatus.INCOMPLETE.value,
            CheckInStatus.ANOMALOUS.value,
        ]:
            try:
                await workflow.wait_condition(
                    lambda: self.user_responded,
                    timeout=timedelta(days=3).total_seconds(),
                )
                if self.user_responded:
                    self.user_responded = False
                    # Attempt to process check-in again
                    check_in_user = UserTrainerIds(
                        user_id=self.user_id,
                        trainer_id=self.trainer_id,
                    )
                    await self._process_check_in(check_in_user)
                    break
            except TimeoutError:
                # User didn't respond within the timeout period
                # might want to send a reminder or take other actions here
                pass

    def calculate_next_check_in_date(self, current_time: datetime) -> datetime:
        next_check_in = current_time + timedelta(minutes=3)
        return next_check_in


tq = "tq"


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[ScheduleCheckInWorkflow],
    ):
        wf_handle = await client.start_workflow(
            ScheduleCheckInWorkflow.run,
            arg=UserTrainerIds("my-user-id", "my-trainer-id"),
            id=str(uuid4()),
            task_queue=tq,
        )

        await wf_handle.signal(ScheduleCheckInWorkflow.set_user_state, "new-user-state")

        await wf_handle.result()


if __name__ == "__main__":
    asyncio.run(main())
