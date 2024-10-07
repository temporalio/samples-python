import asyncio
from datetime import timedelta

from temporalio import client as cl
from temporalio import common as co
from temporalio import workflow as wf

from dan.constants import NAMESPACE, TASK_QUEUE, WORKFLOW_ID


@wf.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @wf.run
    async def run(self) -> str:
        await wf.wait_condition(lambda: self.is_complete)
        return "workflow-result"

    @wf.update
    async def my_update(self) -> str:
        await asyncio.sleep(4)
        self.is_complete = True
        return "update-result"


async def main():
    client = await cl.Client.connect("localhost:7233", namespace=NAMESPACE)
    wf_handle = await client.start_workflow(
        Workflow.run,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_conflict_policy=co.WorkflowIDConflictPolicy.TERMINATE_EXISTING,
        run_timeout=timedelta(seconds=2),
    )
    print(f"Workflow handle: {wf_handle}")

    # up_result = await wf_handle.execute_update(Workflow.my_update)
    # print(f"Update Result: {up_result}")

    up_handle = await wf_handle.start_update(
        Workflow.my_update,
        wait_for_stage=cl.WorkflowUpdateStage.ACCEPTED,
        rpc_timeout=timedelta(seconds=30),
    )
    print(f"Update handle: {up_handle}")
    up_result = await up_handle.result()
    print(f"Update Result: {up_result}")

    wf_result = await wf_handle.result()
    print(f"Workflow Result: {wf_result}")


if __name__ == "__main__":
    asyncio.run(main())
