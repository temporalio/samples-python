from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import activity

import uuid
from datetime import timedelta
from fractions import Fraction

import asyncpg
from temporalio.common import RetryPolicy
from openai_agents.memory.db_utils import IdempotenceHelper
from pydantic import BaseModel
from datetime import datetime
from temporalio.contrib.pydantic import pydantic_data_converter
from typing import Optional


# WARNING: This implementation uses global state and is not safe for concurrent
# testing (e.g., pytest-xdist). Run tests sequentially to avoid race conditions.

# Module-level connection state
_connection: Optional[asyncpg.Connection] = None


def set_worker_connection(connection: asyncpg.Connection) -> None:
    """Set the worker-level database connection."""
    global _connection
    _connection = connection


def get_worker_connection() -> asyncpg.Connection:
    """Get the worker-level database connection.

    Raises:
        RuntimeError: If no connection has been set.
    """
    if _connection is None:
        raise RuntimeError(
            "No worker-level database connection has been set. "
            "Call set_worker_connection() before using activities."
        )
    return _connection


def clear_worker_connection() -> None:
    """Clear the worker-level database connection."""
    global _connection
    _connection = None


@workflow.defn
class FailureFreeTestWorkflow:
    @workflow.run
    async def run(self):
        res1 = await workflow.execute_activity(
            read_only_operation,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=1,
            ),
        )
        assert res1 == 1

        await workflow.execute_activity(
            write_operation,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=1,
            ),
        )
        res2 = await workflow.execute_activity(
            read_test_data,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=1,
            ),
        )
        assert len(res2) == 1 and res2[0] == 456


@workflow.defn
class TestRetriedWriteWorkflow:
    @workflow.run
    async def run(self):
        await workflow.execute_activity(
            fail_mid_transaction_activity,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
            ),
        )
        res = await workflow.execute_activity(
            read_test_data,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=1,
            ),
        )
        assert len(res) == 2
        assert set(res) == {1, 2}

        res2 = await workflow.execute_activity(
            update_and_fail_activity,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
            ),
        )
        assert res2 == 6

        res3 = await workflow.execute_activity(
            read_test_data,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=1,
            ),
        )
        assert len(res3) == 3
        assert set(res3) == {1, 2, 3}


class MyActivityArgs(BaseModel):
    insert_x: int
    insert_y: Fraction
    should_fail: bool


class MyPydanticModel(BaseModel):
    x: int
    y: Fraction
    z: datetime


@workflow.defn
class TestPydanticModelWorkflow:
    @workflow.run
    async def run(self):
        res1 = await workflow.execute_activity(
            write_pydantic_model_activity,
            MyActivityArgs(insert_x=1, should_fail=False, insert_y=Fraction(1, 3)),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=1,
            ),
        )
        assert isinstance(res1, MyPydanticModel)
        assert res1.x == 1
        assert res1.y == Fraction(1, 3)
        assert res1.z is not None
        assert isinstance(res1.z, datetime)

        res2 = await workflow.execute_activity(
            write_pydantic_model_activity,
            MyActivityArgs(insert_x=2, should_fail=True, insert_y=Fraction(4, 5)),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
            ),
        )
        assert isinstance(res2, MyPydanticModel)
        assert res2.x == 2
        assert res2.y == Fraction(4, 5)
        assert res2.z is not None
        assert isinstance(res2.z, datetime)


@activity.defn
async def write_pydantic_model_activity(args: MyActivityArgs) -> MyPydanticModel:
    conn = get_worker_connection()

    async def query(conn):
        await conn.execute(
            "INSERT INTO test (x, y, z) VALUES ($1, $2, NOW())",
            args.insert_x,
            str(args.insert_y),
        )
        result = await conn.fetchrow(
            "SELECT x, y, z FROM test WHERE x = $1 LIMIT 1", args.insert_x
        )
        return MyPydanticModel(x=result[0], y=result[1], z=result[2])

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    res = await idempotence_helper.idempotent_update(conn, query)
    if args.should_fail and activity.info().attempt == 1:
        raise Exception("Test exception")
    return res


@activity.defn
async def read_only_operation():
    conn = get_worker_connection()

    # Read-only operation
    async def query(conn):
        return (await conn.fetchrow("SELECT 1"))[0]

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    record = await idempotence_helper.idempotent_update(conn, query)
    return record


@activity.defn
async def write_operation():
    conn = get_worker_connection()

    async def query(conn):
        await conn.execute("INSERT INTO test (x) VALUES (456)")

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.idempotent_update(conn, query)


@activity.defn
async def read_test_data():
    conn = get_worker_connection()
    # Not using the idempotence helper here because we are just validating
    results = await conn.fetch("SELECT x FROM test")
    return [r[0] for r in results]


@activity.defn
async def fail_mid_transaction_activity():
    conn = get_worker_connection()

    async def query(conn):
        await conn.execute("INSERT INTO test (x) VALUES (1)")
        if activity.info().attempt == 1:
            raise Exception("Test exception")
        await conn.execute("INSERT INTO test (x) VALUES (2)")

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.idempotent_update(conn, query)


@activity.defn
async def update_and_fail_activity():
    # This activity updates the test table and fails after making the update and committing the transaction
    # but before returning the result. This means it needs to read the result from the idempotence table.
    conn = get_worker_connection()

    async def query(conn):
        await conn.execute("INSERT INTO test (x) VALUES (3)")
        result = await conn.fetchrow("SELECT SUM(x) FROM test")
        return result[0]

    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    res = await idempotence_helper.idempotent_update(conn, query)
    if activity.info().attempt == 1:
        raise Exception("Test exception")
    return res


async def test_idempotence_util(client: Client, db_connection: asyncpg.Connection):
    # Set the worker-level connection
    set_worker_connection(db_connection)

    # setup a test table
    await db_connection.execute("CREATE TABLE IF NOT EXISTS test (x INT)")

    # set up the idempotence table
    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    try:
        async with Worker(
            client,
            task_queue=f"test-idempotence-tast-queue-{uuid.uuid4()}",
            workflows=[FailureFreeTestWorkflow],
            activities=[read_only_operation, write_operation, read_test_data],
        ) as worker:
            workflow_handle = await client.start_workflow(
                FailureFreeTestWorkflow.run,
                id=f"test-idempotence-workflow-{uuid.uuid4()}",
                task_queue=worker.task_queue,
                execution_timeout=timedelta(seconds=10),
            )
            await workflow_handle.result()
    finally:
        # Clean up worker-level connection
        clear_worker_connection()


async def test_idempotence_util_retried_write_activity(
    client: Client, db_connection: asyncpg.Connection
):
    # Set the worker-level connection
    set_worker_connection(db_connection)

    # setup a test table
    await db_connection.execute("CREATE TABLE IF NOT EXISTS test (x INT)")

    # set up the idempotence table
    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    try:
        async with Worker(
            client,
            task_queue=f"test-idempotence-tast-queue-{uuid.uuid4()}",
            workflows=[TestRetriedWriteWorkflow],
            activities=[
                fail_mid_transaction_activity,
                read_test_data,
                update_and_fail_activity,
            ],
        ) as worker:
            workflow_handle = await client.start_workflow(
                TestRetriedWriteWorkflow.run,
                id=f"test-idempotence-workflow-{uuid.uuid4()}",
                task_queue=worker.task_queue,
                execution_timeout=timedelta(seconds=10),
            )
            await workflow_handle.result()
    finally:
        # Clean up worker-level connection
        clear_worker_connection()


async def test_pydantic_model_result(client: Client, db_connection: asyncpg.Connection):
    new_config = client.config()
    new_config["data_converter"] = pydantic_data_converter
    client = Client(**new_config)

    # Set the worker-level connection
    set_worker_connection(db_connection)

    # setup a test table
    await db_connection.execute(
        "CREATE TABLE IF NOT EXISTS test (x INT, y TEXT, z TIMESTAMP DEFAULT NOW())"
    )

    # set up the idempotence table
    idempotence_helper = IdempotenceHelper(table_name="activity_idempotence")
    await idempotence_helper.create_table(db_connection)

    try:
        async with Worker(
            client,
            task_queue=f"test-idempotence-tast-queue-{uuid.uuid4()}",
            workflows=[TestPydanticModelWorkflow],
            activities=[write_pydantic_model_activity],
        ) as worker:
            workflow_handle = await client.start_workflow(
                TestPydanticModelWorkflow.run,
                id=f"test-idempotence-workflow-{uuid.uuid4()}",
                task_queue=worker.task_queue,
                execution_timeout=timedelta(seconds=10),
            )
            await workflow_handle.result()
    finally:
        # Clean up worker-level connection
        clear_worker_connection()
