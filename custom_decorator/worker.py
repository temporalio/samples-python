import asyncio
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

from custom_decorator.activity_utils import _auto_heartbeater


# Here we use our automatic heartbeater decorator. If this wasn't present, our
# activity would timeout since it isn't heartbeating.
@activity.defn
@_auto_heartbeater
async def wait_for_cancel_activity() -> str:
    # Wait forever, catch the cancel, and return some value
    try:
        await asyncio.Future()
        raise RuntimeError("unreachable")
    except asyncio.CancelledError:
        return "activity cancelled!"


@workflow.defn
class WaitForCancelWorkflow:
    @workflow.run
    async def run(self) -> str:
        # Start activity and wait on it (it will get cancelled from signal)
        self.activity = workflow.start_activity(
            wait_for_cancel_activity,
            start_to_close_timeout=timedelta(hours=20),
            # We set a heartbeat timeout so Temporal knows if the activity
            # failed/crashed. If we don't heartbeat within this time, Temporal
            # will consider the activity failed.
            heartbeat_timeout=timedelta(seconds=2),
            # Tell the activity not to retry for demonstration purposes only
            retry_policy=RetryPolicy(maximum_attempts=1),
            # Tell the workflow to wait for the post-cancel result
            cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
        return await self.activity

    @workflow.signal
    def cancel_activity(self) -> None:
        self.activity.cancel()


interrupt_event = asyncio.Event()


async def main():
    # Connect client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="custom_decorator-task-queue",
        workflows=[WaitForCancelWorkflow],
        activities=[wait_for_cancel_activity],
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
