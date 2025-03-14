import asyncio
import json
import os
import time

import xray
from opentelemetry import trace
from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils.client import start_workflow


@workflow.defn
class Workflow:
    def __init__(self):
        if os.getenv("TRACING"):
            with xray.start_as_current_span(
                xray.Actor.WORKFLOW_USER,
                name="WorkflowInit",
                workflow_id=workflow.info().workflow_id,
                request_payload="{}",
            ) as span:
                span.add_event("hello from workflow init")
            trace.get_tracer_provider().force_flush()  # type: ignore
            time.sleep(0.5)
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        if os.getenv("TRACING"):
            with xray.start_as_current_span(
                xray.Actor.WORKFLOW_USER,
                name="WorkflowRun",
                workflow_id=workflow.info().workflow_id,
                request_payload="{}",
            ) as span:
                span.add_event("hello from workflow run")
            trace.get_tracer_provider().force_flush()  # type: ignore
            time.sleep(0.5)
        await workflow.wait_condition(lambda: self.is_complete)
        return "workflow-result"

    @workflow.update
    async def my_update(self) -> str:
        if os.getenv("TRACING"):
            with xray.start_as_current_span(
                xray.Actor.WORKFLOW_USER,
                name="HandleWorkflowUpdate",
                workflow_id=workflow.info().workflow_id,
                request_payload="{}",
            ) as span:
                span.add_event("hello from update handler")
                result = await self._my_update()
                span.set_attribute(
                    "rpc.response.payload", json.dumps({"result": result})
                )
            trace.get_tracer_provider().force_flush()  # type: ignore
            time.sleep(0.5)
        else:
            result = await self._my_update()
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
