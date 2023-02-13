import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import NoReturn

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


@dataclass
class ComposeArgsInput:
    arg1: int
    arg2: int


@activity.defn
async def cancel_activity(input: ComposeArgsInput) -> NoReturn:
    try:
        while True:
            print("Heartbeating cancel activity")
            await asyncio.sleep(10)
            activity.heartbeat("some details")
    except asyncio.CancelledError:
        print("Activity cancelled")
        raise


@activity.defn
async def run_activity(input: ComposeArgsInput):
    print("Executing activity")
    return input.arg1 + input.arg2


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, input: ComposeArgsInput):
        workflow.logger.info("Running workflow with parameter %s" % input.arg2)
        try:
            activity_handle = workflow.execute_activity(
                cancel_activity,
                ComposeArgsInput(input.arg1, input.arg2),
                start_to_close_timeout=timedelta(seconds=10),
                heartbeat_timeout=timedelta(seconds=1),
            )

            task = asyncio.create_task(activity_handle)
            await asyncio.sleep(3)
            return task.cancel()
        finally:
            await asyncio.sleep(5)
            activity_handle = workflow.execute_activity(
                run_activity,
                ComposeArgsInput(input.arg1, input.arg2),
                start_to_close_timeout=timedelta(seconds=10),
            )
            return await activity_handle


async def main():

    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue="hello-activity-task-queue",
        workflows=[GreetingWorkflow],
        activities=[cancel_activity, run_activity],
    ):

        result = await client.execute_workflow(
            GreetingWorkflow.run,
            ComposeArgsInput(arg1=3, arg2=2),
            id="hello-activity-workflow-id",
            task_queue="hello-activity-task-queue",
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
