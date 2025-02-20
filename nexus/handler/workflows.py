import asyncio

import xray
from temporalio import workflow

from nexus.service.interface import (
    HelloInput,
    HelloOutput,
)


@workflow.defn
class HelloWorkflow:
    """
    Workflow that backs the `hello` operation.
    """

    @xray.start_as_current_workflow_method_span()
    @workflow.run
    async def run(self, input: HelloInput) -> HelloOutput:
        return HelloOutput(message=f"Hello {input.name}! [from workflow]")

    @workflow.update
    async def my_update(self, input: HelloInput) -> HelloOutput:
        await asyncio.sleep(1)
        return HelloOutput(message=f"Hello {input.name}! [from update]")
