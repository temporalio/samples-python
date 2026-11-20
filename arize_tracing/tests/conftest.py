"""Pytest fixtures for the arize_tracing sample tests.

The sample is its own uv project, so these fixtures replace the ones the
repository root provides to the other samples: a Temporal test environment
(``--workflow-environment local|time-skipping|<address>``) and an in-memory
span exporter behind a fresh replay-safe tracer provider.
"""

import asyncio
from typing import AsyncGenerator, Iterator

import opentelemetry.trace
import pytest
import pytest_asyncio
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.util._once import Once
from temporalio.client import Client
from temporalio.contrib.opentelemetry import create_tracer_provider
from temporalio.testing import WorkflowEnvironment

from telemetry import OpenInferenceEnrichmentProcessor


def pytest_addoption(parser):
    parser.addoption(
        "--workflow-environment",
        default="local",
        help="Which workflow environment to use ('local', 'time-skipping', or target to existing server)",
    )


@pytest.fixture(scope="session")
def event_loop():
    # Session-scoped async fixtures need a session-scoped loop with this
    # version of pytest-asyncio.
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def env(request) -> AsyncGenerator[WorkflowEnvironment, None]:
    env_type = request.config.getoption("--workflow-environment")
    if env_type == "local":
        env = await WorkflowEnvironment.start_local()
    elif env_type == "time-skipping":
        env = await WorkflowEnvironment.start_time_skipping()
    else:
        env = WorkflowEnvironment.from_client(await Client.connect(env_type))
    yield env
    await env.shutdown()


@pytest_asyncio.fixture
async def client(env: WorkflowEnvironment) -> Client:
    return env.client


def _reset_global_tracer_provider() -> None:
    # OpenTelemetry only lets the global provider be set once per process.
    opentelemetry.trace._TRACER_PROVIDER_SET_ONCE = Once()
    opentelemetry.trace._TRACER_PROVIDER = None


@pytest.fixture
def span_exporter() -> Iterator[InMemorySpanExporter]:
    """Install a replay-safe tracer provider with the enrichment processor that
    exports to memory, as the global provider for one test."""
    _reset_global_tracer_provider()
    exporter = InMemorySpanExporter()
    provider = create_tracer_provider()
    provider.add_span_processor(OpenInferenceEnrichmentProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    opentelemetry.trace.set_tracer_provider(provider)
    yield exporter
    _reset_global_tracer_provider()
