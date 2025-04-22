#!/usr/bin/env uv run
import asyncio
import uuid

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

CHILD_WORKFLOW_ID = f"cwid-{uuid.uuid4()}"
WORKFLOW_ID = f"wid-{uuid.uuid4()}"
TASK_QUEUE = "tq"


@workflow.defn
class ChildWorkflow:
    @workflow.run
    async def run(self) -> None:
        await asyncio.Future()


@workflow.defn
class ParentWorkflow:
    @workflow.run
    async def run(self) -> None:
        try:
            child_handle = await workflow.start_child_workflow(
                ChildWorkflow.run, id=CHILD_WORKFLOW_ID
            )
        except Exception as e:
            msg = f"🔴 Exception (1) in ParentWorkflow: {e.__class__.__name__}({e})"
            print(msg)
            if e.__cause__ is not None:
                print(f"\t\tcause: {e.__cause__.__class__.__name__}({e.__cause__})")
            raise

        try:
            await child_handle
        except Exception as e:
            msg = f"🔴 Exception (2) in ParentWorkflow: {e.__class__.__name__}({e})"
            print(msg)
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
            await handle.cancel()
            result = await handle.result()
            print(f"Result: {result}")
        except Exception as e:
            msg = f"🔴 Exception in client:         {e.__class__.__name__}({e})"
            print(msg)
            if e.__cause__ is not None:
                print(f"\t\tcause: {e.__cause__.__class__.__name__}({e.__cause__})")
                if e.__cause__.__cause__ is not None:
                    print(
                        f"\t\t\tcause: {e.__cause__.__cause__.__class__.__name__}({e.__cause__.__cause__})"
                    )


if __name__ == "__main__":
    asyncio.run(main())
