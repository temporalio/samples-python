import asyncio
import json
import time
from typing import cast

from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer
from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils.client import start_workflow
from dan.utils.otel import create_tracer_provider
from dan.utils.xray import start_as_current_workflow_span

provider = create_tracer_provider("Workflow")
tracer = cast(Tracer, provider.get_tracer(__name__))


@workflow.defn
class Workflow:
    def __init__(self):
        with start_as_current_workflow_span(
            tracer=tracer,
            name="WorkflowInit",
            method="WorkflowInit",
            request_type="WorkflowInit",
            request_payload="{}",
            response_type="WorkflowInitResult",
        ) as span:
            span.add_event("hello from workflow init")
        trace.get_tracer_provider().force_flush()  # type: ignore
        time.sleep(5)
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        with start_as_current_workflow_span(
            tracer=tracer,
            name="WorkflowRun",
            method="WorkflowRun",
            request_type="WorkflowRun",
            request_payload="{}",
            response_type="WorkflowRunResult",
        ) as span:
            span.add_event("hello from workflow run")
        trace.get_tracer_provider().force_flush()  # type: ignore
        time.sleep(5)
        await workflow.wait_condition(lambda: self.is_complete)
        return "workflow-result"

    @workflow.update
    async def my_update(self) -> str:
        with start_as_current_workflow_span(
            tracer=tracer,
            name="HandleWorkflowUpdate",
            method="UpdateHandler",
            request_type="WorkflowUpdate",
            request_payload="{}",
            response_type="WorkflowUpdateResult",
        ) as span:
            span.add_event("hello from update handler")
            result = await self._my_update()
            span.set_attribute("rpc.response.payload", json.dumps({"result": result}))
        trace.get_tracer_provider().force_flush()  # type: ignore
        time.sleep(5)
        return result

    async def _my_update(self) -> str:
        self.is_complete = True
        return "update-result"


async def main():
    handle = await start_workflow(Workflow.run)
    update_handle = await handle.start_update(
        Workflow.my_update, wait_for_stage=WorkflowUpdateStage.ACCEPTED
    )
    update_result = await update_handle.result()
    print(f"Update Result: {update_result}")
    result = await handle.result()
    print(f"Workflow Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
