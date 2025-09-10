import asyncio
import multiprocessing
import os
import sys
import uuid
from typing import AsyncGenerator

import asyncpg
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
                "frontend.enableExecuteMultiOperation=true",
            ]
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


@pytest_asyncio.fixture
async def db_connection():
    """Create a PostgreSQL connection with a unique schema for each test.
    
    Sets up a temporary schema with UUID naming, sets it as the default schema
    for the connection, and cleans up with CASCADE on teardown.
    """
    # Generate unique schema name
    schema_name = f"test_{uuid.uuid4().hex}"
    
    # Create connection
    # Note that we read the DATABASE_URL from the environment because asyncpg does not read this
    # environment variable. It does read other postgres environment variables such as PGHOST, 
    # PGPORT, PGDATABASE, PGUSER, and PGPASSWORD, so you can still use those if you do not set
    # DATABASE_URL.
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    try:
        # Create the schema
        await conn.execute(f"CREATE SCHEMA {schema_name}")
        
        # Set the schema as default for this connection
        await conn.execute(f"SET search_path TO {schema_name}")
        
        yield conn
        
    finally:
        # Clean up: drop schema with cascade
        try:
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        except Exception:
            pass  # Best effort cleanup
        await conn.close()
