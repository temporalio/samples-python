"""Worker integration tests for RedisStorageDriver key structure."""

from __future__ import annotations

import dataclasses
import hashlib
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from datetime import timedelta
from typing import Any

import pytest
import pytest_asyncio
import temporalio.converter
from temporalio.client import Client, WorkflowFailureError
from temporalio.converter import ExternalStorage, JSONPlainPayloadConverter
from temporalio.exceptions import ActivityError, ApplicationError
from temporalio.service import RPCError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from external_storage_redis import RedisStorageDriver, RedisStorageDriverClient
from external_storage_redis.redis_asyncio import new_redis_asyncio_client
from external_storage_redis.workflows import (
    LARGE,
    LARGE_2,
    ChildWorkflow,
    DocumentIngestionWorkflow,
    LargeIOWorkflow,
    LargeOutputNoRetryWorkflow,
    ModelTrainingWorkflow,
    OrderFulfillmentWorkflow,
    ParentWithChildWorkflow,
    PaymentProcessingWorkflow,
    SignalQueryUpdateWorkflow,
    download_document,
    extract_text,
    index_document,
    large_io_activity,
    large_output_activity,
)
from tests.external_storage_redis.conftest import KEY_PREFIX

_THRESHOLD = 256


def new_worker(
    client: Client,
    *workflows: type,
    activities: Sequence[Callable[..., Any]] = (),
    task_queue: str | None = None,
    **kwargs: Any,
) -> Worker:
    return Worker(
        client,
        task_queue=task_queue or str(uuid.uuid4()),
        workflows=workflows,
        activities=activities,
        **kwargs,
    )


class FailingSetClient(RedisStorageDriverClient):
    """Redis client wrapper that fails all writes."""

    def __init__(self, delegate: RedisStorageDriverClient) -> None:
        self._delegate = delegate

    async def get(self, *, key: str) -> bytes | None:
        return await self._delegate.get(key=key)

    async def set_if_absent(
        self,
        *,
        key: str,
        data: bytes,
        ttl: timedelta | None = None,
    ) -> bool:
        del key, data, ttl
        raise ConnectionError("Redis is unavailable")


@pytest_asyncio.fixture
async def tmprl_client(
    env: WorkflowEnvironment, redis_asyncio_client: Any
) -> AsyncIterator[Client]:
    """Temporal client wired with ExternalStorage backed by fake Redis."""
    driver = RedisStorageDriver(
        client=new_redis_asyncio_client(redis_asyncio_client),
        key_prefix=KEY_PREFIX,
    )
    yield await Client.connect(
        env.client.service_client.config.target_host,
        namespace=env.client.namespace,
        data_converter=dataclasses.replace(
            temporalio.converter.default(),
            external_storage=ExternalStorage(
                drivers=[driver],
                payload_size_threshold=_THRESHOLD,
            ),
        ),
    )


async def _list_keys(redis_asyncio_client: Any) -> list[str]:
    raw_keys = await redis_asyncio_client.keys(f"{KEY_PREFIX}:*")
    return sorted(key.decode() if isinstance(key, bytes) else key for key in raw_keys)


def _skip_if_standalone_activity_disabled(err: RPCError) -> None:
    if "Standalone activity is disabled" in str(err):
        pytest.skip(
            "Standalone Activity is not supported by this Temporal dev server build"
        )


async def test_redis_driver_workflow_input_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(
        tmprl_client, LargeIOWorkflow, activities=[large_io_activity]
    ) as worker:
        await tmprl_client.execute_workflow(
            LargeIOWorkflow.run,
            LARGE,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert all(
        f"{KEY_PREFIX}:v0:ns:default:wt:LargeIOWorkflow:wi:{workflow_id}:ri:" in key
        for key in keys
    )
    assert sum(1 for key in keys if ":ri:null:" in key) == 1
    assert sum(1 for key in keys if ":ri:null:" not in key) == 1


async def test_redis_driver_workflow_output_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(
        tmprl_client, LargeIOWorkflow, activities=[large_io_activity]
    ) as worker:
        result = await tmprl_client.execute_workflow(
            LargeIOWorkflow.run,
            "small",
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    assert result == LARGE
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 1
    assert (
        f"{KEY_PREFIX}:v0:ns:default:wt:LargeIOWorkflow:wi:{workflow_id}:ri:" in keys[0]
    )
    assert ":ri:null:" not in keys[0]


async def test_redis_driver_workflow_activity_input_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(
        tmprl_client, LargeIOWorkflow, activities=[large_io_activity]
    ) as worker:
        await tmprl_client.execute_workflow(
            LargeIOWorkflow.run,
            LARGE,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert all(
        f"{KEY_PREFIX}:v0:ns:default:wt:LargeIOWorkflow:wi:{workflow_id}:ri:" in key
        for key in keys
    )
    assert all(":ai:" not in key for key in keys)


async def test_redis_driver_workflow_activity_output_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(
        tmprl_client, LargeIOWorkflow, activities=[large_io_activity]
    ) as worker:
        await tmprl_client.execute_workflow(
            LargeIOWorkflow.run,
            "small",
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 1
    assert (
        f"{KEY_PREFIX}:v0:ns:default:wt:LargeIOWorkflow:wi:{workflow_id}:ri:" in keys[0]
    )
    assert ":ri:null:" not in keys[0]


async def test_redis_driver_standalone_activity_input_key(
    env: WorkflowEnvironment,
    tmprl_client: Client,
    redis_asyncio_client: Any,
) -> None:
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/2741"
        )
    activity_id = str(uuid.uuid4())
    task_queue = str(uuid.uuid4())
    async with new_worker(
        tmprl_client, activities=[large_io_activity], task_queue=task_queue
    ):
        try:
            await tmprl_client.execute_activity(
                large_io_activity,
                LARGE,
                id=activity_id,
                task_queue=task_queue,
                start_to_close_timeout=timedelta(seconds=5),
            )
        except RPCError as err:
            _skip_if_standalone_activity_disabled(err)
            raise
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert all(
        f"{KEY_PREFIX}:v0:ns:default:at:large_io_activity:ai:{activity_id}:ri:" in key
        for key in keys
    )
    assert all(":wt:" not in key for key in keys)
    assert sum(1 for key in keys if ":ri:null:" in key) == 1
    assert sum(1 for key in keys if ":ri:null:" not in key) == 1


async def test_redis_driver_standalone_activity_output_key(
    env: WorkflowEnvironment,
    tmprl_client: Client,
    redis_asyncio_client: Any,
) -> None:
    if env.supports_time_skipping:
        pytest.skip(
            "Java test server: https://github.com/temporalio/sdk-java/issues/2741"
        )
    activity_id = str(uuid.uuid4())
    task_queue = str(uuid.uuid4())
    async with new_worker(
        tmprl_client, activities=[large_output_activity], task_queue=task_queue
    ):
        try:
            await tmprl_client.execute_activity(
                large_output_activity,
                id=activity_id,
                task_queue=task_queue,
                start_to_close_timeout=timedelta(seconds=5),
            )
        except RPCError as err:
            _skip_if_standalone_activity_disabled(err)
            raise
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 1
    assert (
        f"{KEY_PREFIX}:v0:ns:default:at:large_output_activity:ai:{activity_id}:ri:"
        in keys[0]
    )
    assert ":ri:null:" not in keys[0]
    assert ":wt:" not in keys[0]


async def test_redis_driver_signal_arg_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(tmprl_client, SignalQueryUpdateWorkflow) as worker:
        handle = await tmprl_client.start_workflow(
            SignalQueryUpdateWorkflow.run,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
        await handle.signal(SignalQueryUpdateWorkflow.finish, LARGE)
        await handle.result()
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert any(
        f"{KEY_PREFIX}:v0:ns:default:wt:null:wi:{workflow_id}:ri:null:" in key
        for key in keys
    )
    assert any(
        f"{KEY_PREFIX}:v0:ns:default:wt:SignalQueryUpdateWorkflow:wi:{workflow_id}:"
        in key
        for key in keys
    )


async def test_redis_driver_query_result_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(tmprl_client, SignalQueryUpdateWorkflow) as worker:
        handle = await tmprl_client.start_workflow(
            SignalQueryUpdateWorkflow.run,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
        result = await handle.query(SignalQueryUpdateWorkflow.get_value, LARGE)
        assert result == LARGE
        await handle.signal(SignalQueryUpdateWorkflow.finish, "done")
        await handle.result()
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert any(
        f"{KEY_PREFIX}:v0:ns:default:wt:null:wi:{workflow_id}:ri:null:" in key
        for key in keys
    )
    assert any(
        f"{KEY_PREFIX}:v0:ns:default:wt:SignalQueryUpdateWorkflow:wi:{workflow_id}:"
        in key
        for key in keys
    )


async def test_redis_driver_update_result_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(tmprl_client, SignalQueryUpdateWorkflow) as worker:
        handle = await tmprl_client.start_workflow(
            SignalQueryUpdateWorkflow.run,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
        result = await handle.execute_update(SignalQueryUpdateWorkflow.do_update, LARGE)
        assert result == LARGE
        await handle.signal(SignalQueryUpdateWorkflow.finish, "done")
        await handle.result()
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert any(
        f"{KEY_PREFIX}:v0:ns:default:wt:null:wi:{workflow_id}:ri:null:" in key
        for key in keys
    )
    assert any(
        f"{KEY_PREFIX}:v0:ns:default:wt:SignalQueryUpdateWorkflow:wi:{workflow_id}:"
        in key
        for key in keys
    )


async def test_redis_driver_child_workflow_input_key(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(
        tmprl_client, ParentWithChildWorkflow, ChildWorkflow
    ) as worker:
        await tmprl_client.execute_workflow(
            ParentWithChildWorkflow.run,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    keys = await _list_keys(redis_asyncio_client)
    child_workflow_id = f"{workflow_id}-child"
    assert len(keys) == 1
    assert (
        f"{KEY_PREFIX}:v0:ns:default:wt:ChildWorkflow:wi:{child_workflow_id}:ri:"
        in keys[0]
    )


async def test_redis_driver_identifier_casing(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = f"MyWorkflow-{uuid.uuid4()}"
    async with new_worker(
        tmprl_client, LargeIOWorkflow, activities=[large_io_activity]
    ) as worker:
        await tmprl_client.execute_workflow(
            LargeIOWorkflow.run,
            LARGE,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert all(
        f"{KEY_PREFIX}:v0:ns:default:wt:LargeIOWorkflow:wi:{workflow_id}:ri:" in key
        for key in keys
    )


async def test_redis_driver_content_dedup(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(
        tmprl_client,
        DocumentIngestionWorkflow,
        activities=[download_document, extract_text, index_document],
    ) as worker:
        await tmprl_client.execute_workflow(
            DocumentIngestionWorkflow.run,
            "doc-001",
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 2
    assert all(
        f"{KEY_PREFIX}:v0:ns:default:wt:DocumentIngestionWorkflow:wi:{workflow_id}:ri:"
        in key
        for key in keys
    )
    assert keys[0] != keys[1]


async def test_redis_driver_single_workflow_same_key_namespace(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    async with new_worker(tmprl_client, ModelTrainingWorkflow) as worker:
        handle = await tmprl_client.start_workflow(
            ModelTrainingWorkflow.run,
            LARGE,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
        metrics = await handle.execute_update(
            ModelTrainingWorkflow.get_metrics, "checkpoint-1"
        )
        assert metrics == LARGE_2
        await handle.signal(ModelTrainingWorkflow.apply_overrides, LARGE)
        await handle.signal(ModelTrainingWorkflow.complete)
        await handle.result()
    keys = await _list_keys(redis_asyncio_client)
    assert len(keys) == 4
    assert all(f":wi:{workflow_id}:" in key for key in keys)


async def test_redis_driver_parent_child_independent_key_namespaces(
    tmprl_client: Client, redis_asyncio_client: Any
) -> None:
    workflow_id = str(uuid.uuid4())
    payment_id = f"{workflow_id}-payment"
    async with new_worker(
        tmprl_client, OrderFulfillmentWorkflow, PaymentProcessingWorkflow
    ) as worker:
        await tmprl_client.execute_workflow(
            OrderFulfillmentWorkflow.run,
            LARGE,
            id=workflow_id,
            task_queue=worker.task_queue,
            execution_timeout=timedelta(seconds=5),
        )
    keys = await _list_keys(redis_asyncio_client)
    parent_keys = [key for key in keys if f":wi:{workflow_id}:" in key]
    child_keys = [key for key in keys if f":wi:{payment_id}:" in key]
    assert len(parent_keys) == 3
    assert len(child_keys) == 1


async def test_redis_store_failure_surfaces_in_workflow_history(
    env: WorkflowEnvironment, driver_client: RedisStorageDriverClient
) -> None:
    driver = RedisStorageDriver(
        client=FailingSetClient(driver_client),
        key_prefix=KEY_PREFIX,
    )
    bad_client = await Client.connect(
        env.client.service_client.config.target_host,
        namespace=env.client.namespace,
        data_converter=dataclasses.replace(
            temporalio.converter.default(),
            external_storage=ExternalStorage(
                drivers=[driver],
                payload_size_threshold=_THRESHOLD,
            ),
        ),
    )
    workflow_id = str(uuid.uuid4())
    async with new_worker(
        bad_client, LargeOutputNoRetryWorkflow, activities=[large_output_activity]
    ) as worker:
        with pytest.raises(WorkflowFailureError) as exc_info:
            await bad_client.execute_workflow(
                LargeOutputNoRetryWorkflow.run,
                id=workflow_id,
                task_queue=worker.task_queue,
                execution_timeout=timedelta(seconds=5),
            )

    large_payload = JSONPlainPayloadConverter().to_payload(LARGE)
    assert large_payload is not None
    expected_hash = hashlib.sha256(large_payload.SerializeToString()).hexdigest()

    activity_error = exc_info.value.__cause__
    assert isinstance(activity_error, ActivityError)
    app_error = activity_error.__cause__
    assert isinstance(app_error, ApplicationError)
    assert app_error.type == "RuntimeError"
    msg = app_error.message
    assert "RedisStorageDriver store failed [key=" in msg
    assert (
        f"{KEY_PREFIX}:v0:ns:default:wt:LargeOutputNoRetryWorkflow:wi:{workflow_id}:ri:"
        in msg
    )
    assert f":d:sha256:{expected_hash}]" in msg
