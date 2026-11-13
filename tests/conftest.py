import asyncio
import gc
import multiprocessing
import sys
from typing import AsyncGenerator, Iterator

import pytest
import pytest_asyncio
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment

# Due to https://github.com/python/cpython/issues/77906, multiprocessing on
# macOS starting with Python 3.8 has changed from "fork" to "spawn". For
# pre-3.8, we are changing it for them.
if sys.version_info < (3, 8) and sys.platform.startswith("darwin"):
    multiprocessing.set_start_method("spawn", True)


def pytest_addoption(parser):
    parser.addoption(
        "--workflow-environment",
        default="local",
        help="Which workflow environment to use ('local', 'time-skipping', or target to existing server)",
    )


@pytest.fixture(scope="session")
def event_loop():
    # See https://github.com/pytest-dev/pytest-asyncio/issues/68
    # See https://github.com/pytest-dev/pytest-asyncio/issues/257
    # Also need ProactorEventLoop on older versions of Python with Windows so
    # that asyncio subprocess works properly
    if sys.version_info < (3, 8) and sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def env(request) -> AsyncGenerator[WorkflowEnvironment, None]:
    env_type = request.config.getoption("--workflow-environment")
    if env_type == "local":
        env = await WorkflowEnvironment.start_local(
            dev_server_extra_args=[
                "--dynamic-config-value",
                "activity.enableCallbacks=true",
                "--dynamic-config-value",
                "history.enableUpdateCallbacks=true",
                "--dynamic-config-value",
                "history.enableCHASMSignalBacklinks=true",
                "--dynamic-config-value",
                "history.enableSignalWithStartFromWorkflow=true",
            ],
            dev_server_download_version="v1.10.0",
        )
    elif env_type == "time-skipping":
        env = await WorkflowEnvironment.start_time_skipping()
    else:
        env = WorkflowEnvironment.from_client(await Client.connect(env_type))
    yield env
    await env.shutdown()


@pytest_asyncio.fixture
async def client(env: WorkflowEnvironment) -> Client:
    return env.client


@pytest.fixture(autouse=True)
def collect_garbage_between_tests() -> Iterator[None]:
    """Run the cyclic garbage collector on the main thread after every test.

    Otherwise objects a test leaves in reference cycles are collected whenever
    an allocation crosses the collector's threshold, which can be on a workflow
    thread in the middle of a sandboxed import. redis-py's ConnectionPool.__del__
    runs an import, and on CPython before 3.12 an import started by a finalizer
    while the same thread is inside importlib's module-lock acquire leaks that
    lock (python/cpython#91351), so the next sandbox import of the same module
    waits forever. That is what stalled the Python 3.10 CI job.
    """
    yield
    gc.collect()
