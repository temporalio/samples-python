#!/usr/bin/env uv run
"""
Parent cancels child.

Child gets                                                 CancelledError
Parent gets:                         ChildWorkflowError -> CancelledError
Client gets: WorkflowFailureError -> ChildWorkflowError -> CancelledError

"""

import asyncio

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

CHILD_WORKFLOW_ID = "cwid"
WORKFLOW_ID = "wid"
TASK_QUEUE = "tq"


@workflow.defn
class ChildWorkflow:
    @workflow.run
    async def run(self) -> None:
        try:
            await asyncio.Future()
        except BaseException as e:
            print(
                f"🔴 Exception caught in ChildWorkflow while awaiting asyncio.Future: {e.__class__.__name__}({e})"
            )
            raise


@workflow.defn
class ParentWorkflow:
    @workflow.run
    async def run(self) -> None:
        child_handle = await workflow.start_child_workflow(
            ChildWorkflow.run, id=CHILD_WORKFLOW_ID
        )
        child_handle.cancel()
        try:
            await child_handle
        except BaseException as e:
            print(
                f"🔴 Exception caught in ParentWorkflow while awaiting child workflow after cancellation request: {e.__class__.__name__}({e})"
            )
            if e.__cause__ is not None:
                print(f"\t\tcause: {e.__cause__.__class__.__name__}({e.__cause__})")
            raise


async def main():
    client = await Client.connect("localhost:7233")

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ParentWorkflow, ChildWorkflow],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        handle = await client.start_workflow(
            ParentWorkflow.run, id=WORKFLOW_ID, task_queue=TASK_QUEUE
        )
        try:
            result = await handle.result()
            print(f"Result: {result}")
        except BaseException as e:
            print(
                f"🔴 Exception caught as client while awaiting workflow: {e.__class__.__name__}({e})"
            )
            if e.__cause__ is not None:
                print(f"\t\tcause: {e.__cause__.__class__.__name__}({e.__cause__})")
                if e.__cause__.__cause__ is not None:
                    print(
                        f"\t\t\tcause: {e.__cause__.__cause__.__class__.__name__}({e.__cause__.__cause__})"
                    )


if __name__ == "__main__":
    asyncio.run(main())
