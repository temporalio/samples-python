import asyncio
from typing import Optional

from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@workflow.defn
class HelloWorldWorkflow:
    def __init__(self):
        self.entity_to_be_greeted: Optional[str] = None

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.entity_to_be_greeted is not None)
        return self.greeting()

    @workflow.update
    async def set_greeting(self, entity_to_be_greeted: str) -> str:
        self.entity_to_be_greeted = entity_to_be_greeted
        return self.greeting()

    @set_greeting.validator
    def set_greeting_validator(self, entity_to_be_greeted: str) -> None:
        # To reject an update, raise an exception.
        if entity_to_be_greeted not in {"world", "World"}:
            raise Exception(f"invalid entity: {entity_to_be_greeted}")

    def greeting(self) -> str:
        return f"Hello, {self.entity_to_be_greeted}!"


async def main():
    client = await Client.connect("localhost:7233")
    async with Worker(
        client,
        task_queue=tq,
        workflows=[HelloWorldWorkflow],
    ):
        handle = await client.start_workflow(
            HelloWorldWorkflow.run,
            id=wid,
            task_queue=tq,
            id_reuse_policy=common.WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        update_result = await handle.execute_update(
            HelloWorldWorkflow.set_greeting, "world"
        )
        print(f"Update Result: {update_result}")
        result = await handle.result()
        print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
