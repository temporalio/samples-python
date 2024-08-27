import asyncio

from temporalio import common, workflow
from temporalio.client import Client

from dan.constants import TASK_QUEUE


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        return "workflow-result"


async def main():
    client = await Client.connect("localhost:7233")
    wf_handle = await client.start_workflow(
        "Workflow",
        id=__file__,
        task_queue=TASK_QUEUE,
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print("workflow handle:", wf_handle)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
