import asyncio
import json
import time

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio import workflow
from temporalio.client import WorkflowUpdateStage

from dan.utils import start_workflow


def get_tracer_provider(service_name: str) -> TracerProvider:
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


provider = get_tracer_provider("Workflow")
tracer = provider.get_tracer(__name__)


@workflow.defn
class Workflow:
    def __init__(self):
        self.is_complete = False

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.is_complete)
        return "workflow-result"

    @workflow.update
    async def my_update(self) -> str:
        with tracer.start_as_current_span("HandleWorkflowUpdate") as span:
            span.set_attribute("rpc.method", "UpdateHandler")
            span.set_attribute("rpc.request.type", "WorkflowUpdate")
            span.set_attribute("rpc.request.payload", "{}")
            span.set_attribute("temporalWorkflowID", workflow.info().workflow_id)
            # span.set_attribute("temporal.worker", True)
            span.set_attribute("temporal.workflow", True)
            result = await self._my_update()
            span.set_attribute("rpc.response.type", "WorkflowUpdateResult")
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
