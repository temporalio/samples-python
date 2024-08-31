import asyncio

from temporalio import common, workflow
from temporalio.client import Client

from dan.constants import NAMESPACE, TASK_QUEUE

wid = "wid"


@workflow.defn
class Workflow:
    def __init__(self, arg: str) -> None:
        pass

    @workflow.run
    async def run(self, arg: str) -> str:
        return f"workflow-result-{arg}"


async def main():
    client = await Client.connect("localhost:7233", namespace=NAMESPACE)
    wf_handle = await client.start_workflow(
        Workflow.run,
        "my-arg",
        id=wid,
        task_queue=TASK_QUEUE,
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
