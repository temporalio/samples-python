import asyncio

from temporalio import workflow

from hello_nexus.service.interface import (
    HelloInput,
    HelloOutput,
)


@workflow.defn
class HelloWorkflow:
    """
    Workflow that backs the `hello` operation.
    """

    @workflow.run
    async def run(self, input: HelloInput) -> HelloOutput:
        await asyncio.sleep(1)  # so that it can be cancelled
        return HelloOutput(message=f"Hello {input.name}! [from workflow]")

    @workflow.update
    async def my_update(self, input: HelloInput) -> HelloOutput:
        await asyncio.sleep(1)
        return HelloOutput(message=f"Hello {input.name}! [from update]")
