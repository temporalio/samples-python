import asyncio

from temporalio import common, workflow
from temporalio.client import Client

from dan.constants import NAMESPACE, TASK_QUEUE

wid = "wid"


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        return "wf-result"


async def main():
    client = await Client.connect("localhost:7233", namespace=NAMESPACE)
    wf_result = await client.execute_workflow(
        Workflow.run,
        id=wid,
        task_queue=TASK_QUEUE,
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(wf_result)


if __name__ == "__main__":
    asyncio.run(main())
