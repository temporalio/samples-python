import asyncio

from temporalio import common, workflow
from temporalio.client import Client

from dan.constants import NAMESPACE, TASK_QUEUE

wid = "wid"


class Mixin:
    def __init__(self, arg: str) -> None:
        # Some unused __init__ method that someone accidentally left on this class.
        self.important_field = arg
        pass


@workflow.defn
class Base:
    def __init__(self, arg: str = "default-value") -> None:
        # Suppose someone deletes this __init__ method because they think it's
        # unnecessary. They have now switched the workflow without warning into
        # "workflow init" mode, and `important_field` will be set equal to the
        # workflow input payload.
        self.important_field = arg

    @workflow.run
    async def run(self, arg: str) -> str:
        self.important_field = "some-value"
        ...
        return self.important_field


@workflow.defn
class Workflow(Base, Mixin):
    @workflow.run
    async def run(self, arg: str) -> str:
        return self.important_field


async def main():
    try:
        client = await Client.connect("localhost:7233", namespace=NAMESPACE)
    except Exception as e:
        import pdb

        pdb.set_trace()
        print(e)
    wf_result = await client.execute_workflow(
        Workflow.run,
        "workflow-input",
        id=wid,
        task_queue=TASK_QUEUE,
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(wf_result)


if __name__ == "__main__":
    asyncio.run(main())
