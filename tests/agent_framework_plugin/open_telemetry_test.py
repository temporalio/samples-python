import uuid

import opentelemetry.trace
import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin, create_tracer_provider
from temporalio.worker import Worker

from agent_framework_plugin.open_telemetry.workflow import TracedWorkflow
from tests.agent_framework_plugin._fake_chat_client import scripted_plugin
from tests.agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    count_scheduled_activities,
)


async def test_model_activity_span_joins_the_trace(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    exporter = InMemorySpanExporter()
    provider = create_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Other test modules install their provider with set_tracer_provider,
    # which works once per process. Make this one the global for the duration
    # of the test only, so the modules stay independent of their order.
    monkeypatch.setattr(opentelemetry.trace, "_TRACER_PROVIDER", provider)

    plugin, _ = scripted_plugin(["Traced reply."])
    config = client.config()
    config["plugins"] = [
        *config["plugins"],
        OpenTelemetryPlugin(add_temporal_spans=True),
        plugin,
    ]
    client = Client(**config)
    task_queue = f"agent-framework-open-telemetry-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[TracedWorkflow],
        max_cached_workflows=0,
    ):
        tracer = opentelemetry.trace.get_tracer(__name__)
        with tracer.start_as_current_span("ask-agent") as root:
            handle = await client.start_workflow(
                TracedWorkflow.run,
                "What is durable execution?",
                id=f"agent-framework-open-telemetry-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            result = await handle.result()

    assert result == "Traced reply."
    assert await count_scheduled_activities(handle) == {INVOKE_MODEL: 1}

    trace_id = root.get_span_context().trace_id
    spans = {span.name: span for span in exporter.get_finished_spans()}
    # The model Activity and the Workflow run are spans of the caller's trace.
    for name in ("RunWorkflow:TracedWorkflow", f"RunActivity:{INVOKE_MODEL}"):
        assert name in spans, sorted(spans)
        assert spans[name].context.trace_id == trace_id
    assert spans[f"RunActivity:{INVOKE_MODEL}"].parent is not None
