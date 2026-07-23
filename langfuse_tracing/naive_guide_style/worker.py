"""ANTI-PATTERN worker — deliberately broken. Do not copy.

Mirrors the Langfuse Temporal guide's setup: a plain (not replay-safe)
OpenTelemetry tracer provider exporting to Langfuse, global OpenAI
instrumentation, and no Temporal OpenTelemetry integration. The workflow
above additionally opts out of the sandbox, as the guide instructs.

The worker runs with the workflow cache disabled (``max_cached_workflows=0``)
so that replay — which in production happens on worker restarts, deploys, and
cache evictions — happens on every workflow task, making the breakage
immediately visible. See README.md for the experiment.
"""

import asyncio
import base64
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from langfuse_tracing.naive_guide_style.workflow import (
    NaiveGuideStyleWorkflow,
    naive_llm_step,
)
from langfuse_tracing.telemetry import instrument_openai

TASK_QUEUE = "langfuse-naive-guide-style-task-queue"


def setup_plain_tracing() -> None:
    # ANTI-PATTERN: a plain TracerProvider. Span IDs are random and export is
    # unconditional, so workflow replay re-emits spans as brand-new data.
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    auth = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: "naive-guide-style-worker"})
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{host}/api/public/otel/v1/traces",
                headers={
                    "Authorization": f"Basic {auth}",
                    "x-langfuse-ingestion-version": "4",
                },
            ),
            schedule_delay_millis=500,
        )
    )
    trace.set_tracer_provider(provider)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    setup_plain_tracing()
    instrument_openai()

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    # ANTI-PATTERN: no OpenTelemetryPlugin — no replay safety, no context
    # propagation across the workflow/activity boundary.
    client = await Client.connect(**config)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[NaiveGuideStyleWorkflow],
        activities=[naive_llm_step],
        max_cached_workflows=0,
    )
    print("ANTI-PATTERN worker started (do not copy this setup), ctrl+c to exit")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
