import asyncio
import os
from typing import cast

from opentelemetry.sdk.trace import Tracer
from temporalio import workflow
from temporalio_xray import start_as_current_workflow_span

from dan.utils.client import start_workflow
from dan.utils.otel import create_tracer_provider

provider = create_tracer_provider("Workflow")
tracer = cast(Tracer, provider.get_tracer(__name__))


@workflow.defn
class Workflow:
    @workflow.run
    async def run(self) -> str:
        if os.getenv("TRACING"):
            print("🩻")
            with start_as_current_workflow_span(
                name="WorkflowInit",
                workflow_id=workflow.info().workflow_id,
                method="WorkflowInit",
                request_type="WorkflowInit",
                request_payload="{}",
                response_type="WorkflowInitResult",
            ) as span:
                span.add_event("hello from workflow init")
            # trace.get_tracer_provider().force_flush()  # type: ignore
            # time.sleep(0.5)
        return "workflow-result"


async def main():
    wf_handle = await start_workflow(Workflow.run)
    print("workflow handle:", wf_handle)
    print("workflow result:", await wf_handle.result())


if __name__ == "__main__":
    asyncio.run(main())
