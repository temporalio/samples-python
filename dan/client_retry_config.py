import asyncio

from temporalio import common, workflow
from temporalio.client import Client, WorkflowUpdateStage
from temporalio.service import RetryConfig

from dan.constants import TASK_QUEUE


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: False)
        return "workflow-result"

    @workflow.query
    def my_query(self) -> str:
        # assert False
        return "query-result"

    @workflow.signal
    async def my_signal(self):
        pass

    @workflow.update
    async def my_update(self) -> str:
        # await asyncio.sleep(5)
        # assert False
        return "update-result"


async def main():
    client = await Client.connect(
        "localhost:7233",
        retry_config=RetryConfig(max_elapsed_time_millis=7000, max_retries=1),
    )
    wf_handle = await client.start_workflow(
        Workflow.run,
        id=__file__,
        task_queue=TASK_QUEUE,
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )

    print("waiting for update acceptance...")
    async with asyncio.timeout(5):
        update_handle = await wf_handle.start_update(
            Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
        )

    print("waiting for update result...")
    print("update result:", await update_handle.result())

    print("waiting for wf result...")
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
