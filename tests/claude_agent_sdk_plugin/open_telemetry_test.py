import asyncio
import json
import os
import threading
import uuid
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import opentelemetry.trace
import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin, create_tracer_provider
from temporalio.worker import Worker

from claude_agent_sdk_plugin.offline import scripted_api
from claude_agent_sdk_plugin.open_telemetry.run_worker import OFFLINE_ANSWERS
from claude_agent_sdk_plugin.open_telemetry.telemetry import CLAUDE_CODE_TRACING
from claude_agent_sdk_plugin.open_telemetry.workflow import OpenTelemetryWorkflow


@pytest.fixture
def otlp_collector() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Claude Code's spans, as it exports them over OTLP/HTTP JSON."""
    spans: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            spans.extend(
                span
                for resource in body.get("resourceSpans", [])
                for scope in resource["scopeSpans"]
                for span in scope["spans"]
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", spans
    server.shutdown()
    server.server_close()


async def test_claude_code_spans_join_the_workflow_trace(
    client: Client, otlp_collector: tuple[str, list[dict[str, Any]]]
) -> None:
    endpoint, claude_code_spans = otlp_collector
    exporter = InMemorySpanExporter()
    provider = create_tracer_provider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    opentelemetry.trace.set_tracer_provider(provider)

    config = client.config()
    config["plugins"] = [OpenTelemetryPlugin(add_temporal_spans=True)]
    client = Client(**config)
    task_queue = f"claude-agent-sdk-open-telemetry-{uuid.uuid4()}"

    with scripted_api(OFFLINE_ANSWERS):
        os.environ.update(
            {
                **CLAUDE_CODE_TRACING,
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json",
                "OTEL_EXPORTER_OTLP_ENDPOINT": endpoint,
                "OTEL_TRACES_EXPORT_INTERVAL": "100",
            }
        )
        try:
            async with Worker(
                client,
                task_queue=task_queue,
                workflows=[OpenTelemetryWorkflow],
                plugins=[ClaudeAgentSDKPlugin()],
            ):
                tracer = opentelemetry.trace.get_tracer(__name__)
                with tracer.start_as_current_span("ask-agent") as root:
                    result = await client.execute_workflow(
                        OpenTelemetryWorkflow.run,
                        "How many Python files are in the current directory?",
                        id=f"open-telemetry-{uuid.uuid4()}",
                        task_queue=task_queue,
                    )
        finally:
            for name in CLAUDE_CODE_TRACING:
                os.environ.pop(name, None)
            os.environ.pop("OTEL_TRACES_EXPORT_INTERVAL", None)

    assert result == "I counted the Python files with ls."

    # Claude Code exports on its own schedule, and on exit.
    for _ in range(50):
        if any(s["name"] == "claude_code.interaction" for s in claude_code_spans):
            break
        await asyncio.sleep(0.1)

    trace_id = format(root.get_span_context().trace_id, "032x")
    [connect] = [
        span
        for span in exporter.get_finished_spans()
        if span.name == "RunActivity:claude-agent-sdk-connect"
    ]
    [interaction] = [
        span for span in claude_code_spans if span["name"] == "claude_code.interaction"
    ]
    assert interaction["traceId"] == trace_id
    assert interaction["parentSpanId"] == format(connect.context.span_id, "016x")
    assert {span["name"] for span in claude_code_spans} >= {
        "claude_code.llm_request",
        "claude_code.tool",
    }
    assert {span["traceId"] for span in claude_code_spans} == {trace_id}
