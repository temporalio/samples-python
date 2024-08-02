import asyncio
from dataclasses import dataclass
from typing import Optional

from temporalio import common, workflow
from temporalio.client import Client
from temporalio.worker import Worker

wid = __file__
tq = "tq"


@dataclass
class HelloWorldInput:
    greeting: str


@workflow.defn
class HelloWorldWorkflow:
    def __init__(self):
        self.greeting: Optional[str] = None

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.greeting is not None)
        return f"{self.greeting}, world!"

    @workflow.update
    def set_greeting(self, input: HelloWorldInput) -> Optional[str]:
        previous_greeting, self.greeting = self.greeting, input.greeting
        return previous_greeting

    @set_greeting.validator
    def set_greeting_validator(self, input: HelloWorldInput) -> None:
        if input.greeting.lower() not in {"hello", "hola"}:
            raise Exception(f"invalid greeting: {input.greeting}")


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
            HelloWorldWorkflow.set_greeting, HelloWorldInput("Hola")
        )
        print(f"Update Result: {update_result}")
        result = await handle.result()
        print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
