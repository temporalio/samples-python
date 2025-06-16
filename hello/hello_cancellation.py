import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import NoReturn

from temporalio import activity, workflow
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import CancelledError
from temporalio.worker import Worker


@activity.defn
def never_complete_activity() -> NoReturn:
    # All long-running activities should heartbeat. Heartbeat is how
    # cancellation is delivered from the server.
    try:
        while True:
            print("Heartbeating activity")
            activity.heartbeat()
            time.sleep(1)
    except CancelledError:
        print("Activity cancelled")
        raise


@activity.defn
def cleanup_activity() -> None:
    print("Executing cleanup activity")


@workflow.defn
class CancellationWorkflow:
    @workflow.run
    async def run(self) -> None:
        # Execute the forever running activity, and do a cleanup activity when
        # it is complete (on error or cancel)
        try:
            await workflow.execute_activity(
                never_complete_activity,
                start_to_close_timeout=timedelta(seconds=1000),
                # Always set a heartbeat timeout for long-running activities
                heartbeat_timeout=timedelta(seconds=2),
            )
        finally:
            await workflow.execute_activity(
                cleanup_activity, start_to_close_timeout=timedelta(seconds=5)
            )


async def main():
    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-cancellation-task-queue",
        workflows=[CancellationWorkflow],
        activities=[never_complete_activity, cleanup_activity],
        activity_executor=ThreadPoolExecutor(5),
    ):

        # While the worker is running, use the client to start the workflow.
        # Note, in many production setups, the client would be in a completely
        # separate process from the worker.
        handle = await client.start_workflow(
            CancellationWorkflow.run,
            id="hello-cancellation-workflow-id",
            task_queue="hello-cancellation-task-queue",
        )

        # Now that we've started, wait a couple of seconds then cancel it
        await asyncio.sleep(2)
        await handle.cancel()

        # Now wait on the result which we expect will fail since it was
        # cancelled
        try:
            await handle.result()
            raise RuntimeError("Should not succeed")
        except WorkflowFailureError:
            print("Got expected exception: ", traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
