"""Pytest fixtures for the arize_tracing sample tests.

The sample is its own uv project, so these fixtures replace the ones the
repository root provides to the other samples: a Temporal test environment
(``--workflow-environment local|time-skipping|<address>``) and a reset of the
global OpenTelemetry tracer provider so each test can install its own.
"""

import asyncio
from typing import AsyncGenerator, Iterator

import opentelemetry.trace
import pytest
import pytest_asyncio
from opentelemetry.util._once import Once
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment


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


@pytest.fixture
def reset_otel_tracer_provider() -> Iterator[None]:
    """Reset global OpenTelemetry tracer provider state around a test.

    OpenTelemetry only allows the global tracer provider to be set once per
    process; tests that install their own provider need this reset.
    """
    opentelemetry.trace._TRACER_PROVIDER_SET_ONCE = Once()
    opentelemetry.trace._TRACER_PROVIDER = None
    yield
    opentelemetry.trace._TRACER_PROVIDER_SET_ONCE = Once()
    opentelemetry.trace._TRACER_PROVIDER = None
