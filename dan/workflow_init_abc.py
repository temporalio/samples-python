import asyncio
from abc import ABC, abstractmethod

from temporalio import common, workflow
from temporalio.client import Client

from dan.constants import NAMESPACE, TASK_QUEUE

wid = "wid"


@workflow.defn(name="my-workflow")
class WorkflowInterface(ABC):
    def __init__(self, some_val_set_by_subclass: str) -> None:
        self.some_val_set_by_subclass = some_val_set_by_subclass

    @abstractmethod
    @workflow.run
    async def run(self) -> str: ...


@workflow.defn(name="my-workflow")
class Workflow(WorkflowInterface):
    def __init__(self) -> None:
        super().__init__("my-specific-value")

    @workflow.run
    async def run(self) -> str:
        return f"Result: {self.some_val_set_by_subclass}"


async def main():
    client = await Client.connect("localhost:7233", namespace=NAMESPACE)
    wf_result = await client.execute_workflow(
        WorkflowInterface.run,
        id=wid,
        task_queue=TASK_QUEUE,
        id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(wf_result)


if __name__ == "__main__":
    asyncio.run(main())
