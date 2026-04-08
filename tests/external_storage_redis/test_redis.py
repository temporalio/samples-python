"""Unit tests for RedisStorageDriver using fakeredis."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Coroutine
from datetime import timedelta
from functools import wraps
from typing import Any
from unittest.mock import MagicMock

import fakeredis.aioredis
import pytest

from temporalio.api.common.v1 import Payload
from temporalio.converter import (
    JSONPlainPayloadConverter,
    StorageDriverActivityInfo,
    StorageDriverClaim,
    StorageDriverRetrieveContext,
    StorageDriverStoreContext,
    StorageDriverWorkflowInfo,
)
from temporalio.exceptions import ApplicationError

from external_storage_redis import RedisStorageDriver, RedisStorageDriverClient
from external_storage_redis.redis_asyncio import new_redis_asyncio_client
from tests.external_storage_redis.conftest import KEY_PREFIX

_CONVERTER = JSONPlainPayloadConverter()


def make_payload(value: str = "hello") -> Payload:
    payload = _CONVERTER.to_payload(value)
    assert payload is not None
    return payload


def make_store_context(
    target: StorageDriverActivityInfo | StorageDriverWorkflowInfo | None = None,
) -> StorageDriverStoreContext:
    return StorageDriverStoreContext(target=target)


def make_workflow_context(
    namespace: str = "my-namespace",
    workflow_id: str = "my-workflow",
    workflow_type: str | None = None,
    run_id: str | None = None,
) -> StorageDriverStoreContext:
    return make_store_context(
        target=StorageDriverWorkflowInfo(
            id=workflow_id,
            type=workflow_type,
            run_id=run_id,
            namespace=namespace,
        )
    )


def make_activity_context(
    namespace: str = "my-namespace",
    activity_id: str | None = "my-activity",
    activity_type: str | None = None,
    run_id: str | None = None,
) -> StorageDriverStoreContext:
    return make_store_context(
        target=StorageDriverActivityInfo(
            id=activity_id,
            type=activity_type,
            run_id=run_id,
            namespace=namespace,
        )
    )


async def _list_keys(redis_asyncio_client: Any) -> list[str]:
    raw_keys = await redis_asyncio_client.keys("*")
    return sorted(key.decode() if isinstance(key, bytes) else key for key in raw_keys)


async def _wait_for_key_absent(redis_asyncio_client: Any, key: str) -> None:
    async def _poll() -> None:
        while await redis_asyncio_client.exists(key):
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_poll(), timeout=2)


class CountingDriverClient(RedisStorageDriverClient):
    """RedisStorageDriverClient wrapper that counts calls."""

    def __init__(self, delegate: RedisStorageDriverClient) -> None:
        self._delegate = delegate
        self.get_count = 0
        self.set_if_absent_count = 0
        self.insert_count = 0

    async def get(self, *, key: str) -> bytes | None:
        self.get_count += 1
        return await self._delegate.get(key=key)

    async def set_if_absent(
        self,
        *,
        key: str,
        data: bytes,
        ttl: timedelta | None = None,
    ) -> bool:
        self.set_if_absent_count += 1
        inserted = await self._delegate.set_if_absent(key=key, data=data, ttl=ttl)
        if inserted:
            self.insert_count += 1
        return inserted


class FailOnceDriverClient(RedisStorageDriverClient):
    """RedisStorageDriverClient wrapper that fails one call then blocks."""

    def __init__(self, delegate: RedisStorageDriverClient, fail_on: str) -> None:
        self._delegate = delegate
        self._fail_on = fail_on
        self._call_count = 0
        self.cancelled: list[bool] = []

    async def _maybe_fail(self) -> None:
        self._call_count += 1
        if self._call_count == 1:
            raise ConnectionError("Redis connection lost")
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.cancelled.append(True)
            raise

    async def get(self, *, key: str) -> bytes | None:
        if self._fail_on == "get":
            await self._maybe_fail()
        return await self._delegate.get(key=key)

    async def set_if_absent(
        self,
        *,
        key: str,
        data: bytes,
        ttl: timedelta | None = None,
    ) -> bool:
        if self._fail_on == "set_if_absent":
            await self._maybe_fail()
        return await self._delegate.set_if_absent(key=key, data=data, ttl=ttl)


class _AsyncBarrier:
    """Minimal asyncio.Barrier equivalent for Python <3.11."""

    def __init__(self, parties: int) -> None:
        self._parties = parties
        self._count = 0
        self._event = asyncio.Event()

    async def wait(self) -> None:
        self._count += 1
        if self._count >= self._parties:
            self._event.set()
        else:
            await self._event.wait()


def _barrier_wrapper(
    fn: Callable[..., Coroutine[Any, Any, Any]], barrier: _AsyncBarrier
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Wrap an async method to wait at a barrier before proceeding."""

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        await asyncio.wait_for(barrier.wait(), timeout=5)
        return await fn(*args, **kwargs)

    return wrapper


@pytest.fixture
def counting_driver_client(
    driver_client: RedisStorageDriverClient,
) -> CountingDriverClient:
    """Wrap the driver client in a counting decorator."""
    return CountingDriverClient(driver_client)


class TestRedisStorageDriverInit:
    def test_default_name(self) -> None:
        driver = RedisStorageDriver(client=MagicMock(spec=RedisStorageDriverClient))
        assert driver.name() == "redis"

    def test_custom_name(self) -> None:
        driver = RedisStorageDriver(
            client=MagicMock(spec=RedisStorageDriverClient),
            driver_name="my-redis",
        )
        assert driver.name() == "my-redis"

    def test_type(self) -> None:
        driver = RedisStorageDriver(client=MagicMock(spec=RedisStorageDriverClient))
        assert driver.type() == "redis"

    def test_ttl_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="ttl must be greater than zero"):
            RedisStorageDriver(
                client=MagicMock(spec=RedisStorageDriverClient),
                ttl=timedelta(0),
            )

    def test_ttl_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="ttl must be greater than zero"):
            RedisStorageDriver(
                client=MagicMock(spec=RedisStorageDriverClient),
                ttl=timedelta(seconds=-1),
            )

    def test_max_payload_size_zero_raises(self) -> None:
        with pytest.raises(
            ValueError, match="max_payload_size must be greater than zero"
        ):
            RedisStorageDriver(
                client=MagicMock(spec=RedisStorageDriverClient),
                max_payload_size=0,
            )

    def test_max_payload_size_negative_raises(self) -> None:
        with pytest.raises(
            ValueError, match="max_payload_size must be greater than zero"
        ):
            RedisStorageDriver(
                client=MagicMock(spec=RedisStorageDriverClient),
                max_payload_size=-1,
            )


class TestRedisStorageDriverKeyConstruction:
    async def test_key_context_none(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        [claim] = await driver.store(make_store_context(), [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert claim.claim_data["key"] == f"{KEY_PREFIX}:v0:d:sha256:{expected_hash}"

    async def test_key_context_workflow(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_workflow_context(namespace="ns1", workflow_id="wf1")
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:ns1:wt:null:wi:wf1:ri:null:d:sha256:{expected_hash}"
        )

    async def test_key_context_workflow_with_type_and_run_id(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_workflow_context(
            namespace="ns1",
            workflow_id="wf1",
            workflow_type="MyWorkflow",
            run_id="run-abc",
        )
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:ns1:wt:MyWorkflow:wi:wf1:ri:run-abc:d:sha256:{expected_hash}"
        )

    async def test_key_context_activity(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_activity_context(namespace="ns1", activity_id="act1")
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:ns1:at:null:ai:act1:ri:null:d:sha256:{expected_hash}"
        )

    async def test_key_context_activity_with_type_and_run_id(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_activity_context(
            namespace="ns1",
            activity_id="act1",
            activity_type="MyActivity",
            run_id="run-abc",
        )
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:ns1:at:MyActivity:ai:act1:ri:run-abc:d:sha256:{expected_hash}"
        )

    async def test_key_preserves_case(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_workflow_context(namespace="MyNamespace", workflow_id="MyWorkflow")
        [claim] = await driver.store(ctx, [payload])
        key = claim.claim_data["key"]
        assert "MyNamespace" in key
        assert "MyWorkflow" in key

    async def test_key_urlencodes_workflow_id_with_slashes(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_workflow_context(namespace="ns1", workflow_id="order/123/v2")
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:ns1:wt:null:wi:order%2F123%2Fv2:ri:null:d:sha256:{expected_hash}"
        )

    async def test_key_urlencodes_workflow_id_with_special_chars(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_workflow_context(namespace="ns1", workflow_id="wf#1 &foo=bar")
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:ns1:wt:null:wi:wf%231%20%26foo%3Dbar:ri:null:d:sha256:{expected_hash}"
        )

    async def test_key_urlencodes_activity_id(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_activity_context(namespace="ns1", activity_id="act/1#2")
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:ns1:at:null:ai:act%2F1%232:ri:null:d:sha256:{expected_hash}"
        )

    async def test_key_urlencodes_namespace(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        ctx = make_workflow_context(namespace="my/ns#1", workflow_id="wf1")
        [claim] = await driver.store(ctx, [payload])
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert (
            claim.claim_data["key"]
            == f"{KEY_PREFIX}:v0:ns:my%2Fns%231:wt:null:wi:wf1:ri:null:d:sha256:{expected_hash}"
        )

    async def test_key_urlencoded_roundtrip(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload("special-char-roundtrip")
        ctx = make_workflow_context(namespace="ns/1", workflow_id="wf/2#3")
        [claim] = await driver.store(ctx, [payload])
        [retrieved] = await driver.retrieve(StorageDriverRetrieveContext(), [claim])
        assert retrieved == payload


class TestRedisStorageDriverStoreRetrieve:
    async def test_store_returns_claim_with_key_and_hash(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        [claim] = await driver.store(make_store_context(), [payload])
        assert claim.claim_data["key"].startswith(f"{KEY_PREFIX}:v0:")
        assert claim.claim_data["hash_algorithm"] == "sha256"
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        assert claim.claim_data["hash_value"] == expected_hash

    async def test_roundtrip_single_payload(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload("round-trip value")
        [claim] = await driver.store(make_store_context(), [payload])
        [retrieved] = await driver.retrieve(StorageDriverRetrieveContext(), [claim])
        assert retrieved == payload

    async def test_roundtrip_multiple_payloads(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payloads = [make_payload(f"value-{i}") for i in range(3)]
        claims = await driver.store(make_store_context(), payloads)
        retrieved = await driver.retrieve(StorageDriverRetrieveContext(), claims)
        assert retrieved == payloads

    async def test_empty_payloads_returns_empty_list(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        assert await driver.store(make_store_context(), []) == []
        assert await driver.retrieve(StorageDriverRetrieveContext(), []) == []

    async def test_content_addressable_deduplication(
        self, redis_asyncio_client: Any, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload("same-value")
        claims = await driver.store(make_store_context(), [payload, payload])
        assert claims[0].claim_data["key"] == claims[1].claim_data["key"]
        assert await _list_keys(redis_asyncio_client) == [claims[0].claim_data["key"]]

    async def test_set_if_absent_only_inserts_once(
        self, counting_driver_client: CountingDriverClient
    ) -> None:
        driver = RedisStorageDriver(
            client=counting_driver_client,
            key_prefix=KEY_PREFIX,
        )
        payload = make_payload("insert-once")

        await driver.store(make_store_context(), [payload])
        await driver.store(make_store_context(), [payload])

        assert counting_driver_client.set_if_absent_count == 2
        assert counting_driver_client.insert_count == 1

    async def test_duplicate_store_preserves_data(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload("preserve-me")

        [claim1] = await driver.store(make_store_context(), [payload])
        [claim2] = await driver.store(make_store_context(), [payload])
        assert claim1 == claim2

        [retrieved] = await driver.retrieve(StorageDriverRetrieveContext(), [claim2])
        assert retrieved == payload

    async def test_ttl_is_applied_on_first_write(
        self, redis_asyncio_client: Any, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(
            client=driver_client,
            key_prefix=KEY_PREFIX,
            ttl=timedelta(seconds=5),
        )
        [claim] = await driver.store(make_store_context(), [make_payload("ttl")])
        ttl_ms = await redis_asyncio_client.pttl(claim.claim_data["key"])
        assert 0 < ttl_ms <= 5000

    async def test_ttl_is_not_refreshed_on_duplicate_write(
        self, redis_asyncio_client: Any, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(
            client=driver_client,
            key_prefix=KEY_PREFIX,
            ttl=timedelta(seconds=5),
        )
        payload = make_payload("ttl-stable")
        [claim] = await driver.store(make_store_context(), [payload])
        first_ttl_ms = await redis_asyncio_client.pttl(claim.claim_data["key"])
        await asyncio.sleep(0.02)
        await driver.store(make_store_context(), [payload])
        second_ttl_ms = await redis_asyncio_client.pttl(claim.claim_data["key"])
        assert 0 < second_ttl_ms < first_ttl_ms

    async def test_retrieve_validates_hash(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload("check-integrity")
        [claim] = await driver.store(make_store_context(), [payload])

        tampered_claim = StorageDriverClaim(
            claim_data={
                **claim.claim_data,
                "hash_value": "0" * 64,
            },
        )
        with pytest.raises(
            ValueError,
            match=r"RedisStorageDriver integrity check failed \[key=.+\]: expected sha256:.+, got sha256:.+",
        ):
            await driver.retrieve(StorageDriverRetrieveContext(), [tampered_claim])

    async def test_retrieve_rejects_unsupported_hash_algorithm(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload("unsupported-algo")
        [claim] = await driver.store(make_store_context(), [payload])

        bad_claim = StorageDriverClaim(
            claim_data={
                **claim.claim_data,
                "hash_algorithm": "md5",
            },
        )
        with pytest.raises(
            ValueError,
            match=r"RedisStorageDriver unsupported hash algorithm \[key=.+\]: expected sha256, got md5",
        ):
            await driver.retrieve(StorageDriverRetrieveContext(), [bad_claim])

    async def test_retrieve_without_hash_in_claim(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payload = make_payload("no-hash-claim")
        [claim] = await driver.store(make_store_context(), [payload])

        legacy_claim = StorageDriverClaim(
            claim_data={
                "key": claim.claim_data["key"],
            },
        )
        [retrieved] = await driver.retrieve(
            StorageDriverRetrieveContext(), [legacy_claim]
        )
        assert retrieved == payload

    async def test_retrieve_missing_key_raises_non_retryable_application_error(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        claim = StorageDriverClaim(
            claim_data={"key": f"{KEY_PREFIX}:v0:d:sha256:missing"}
        )
        with pytest.raises(ApplicationError) as exc_info:
            await driver.retrieve(StorageDriverRetrieveContext(), [claim])
        assert exc_info.value.message == (
            f"Payload not found for key '{KEY_PREFIX}:v0:d:sha256:missing'"
        )
        assert exc_info.value.type == "PayloadNotFoundError"
        assert exc_info.value.non_retryable is True

    async def test_expired_key_raises_non_retryable_application_error(
        self, redis_asyncio_client: Any, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(
            client=driver_client,
            key_prefix=KEY_PREFIX,
            ttl=timedelta(milliseconds=10),
        )
        [claim] = await driver.store(make_store_context(), [make_payload("expire-me")])
        await _wait_for_key_absent(redis_asyncio_client, claim.claim_data["key"])
        with pytest.raises(ApplicationError) as exc_info:
            await driver.retrieve(StorageDriverRetrieveContext(), [claim])
        assert exc_info.value.type == "PayloadNotFoundError"
        assert exc_info.value.non_retryable is True

    async def test_payload_exceeds_max_size_raises(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(
            client=driver_client,
            key_prefix=KEY_PREFIX,
            max_payload_size=10,
        )
        with pytest.raises(
            ValueError,
            match=r"Payload size \d+ bytes exceeds the configured max_payload_size of 10 bytes",
        ):
            await driver.store(make_store_context(), [make_payload("exceeds-limit")])

    async def test_payload_at_max_size_succeeds(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        payload = make_payload("x")
        driver = RedisStorageDriver(
            client=driver_client,
            key_prefix=KEY_PREFIX,
            max_payload_size=len(payload.SerializeToString()),
        )
        await driver.store(make_store_context(), [payload])


class TestRedisAsyncioAdapter:
    async def test_decode_responses_client_raises(self) -> None:
        client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        try:
            await client.set("adapter:text", b"abc")
            adapter = new_redis_asyncio_client(client)
            with pytest.raises(TypeError, match="decode_responses=False"):
                await adapter.get(key="adapter:text")
        finally:
            aclose = getattr(client, "aclose", None)
            if aclose is not None:
                await aclose()
            else:
                await client.close()


class TestRedisStorageDriverErrors:
    async def test_store_client_failure_raises(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        faulty_client = FailOnceDriverClient(
            delegate=driver_client, fail_on="set_if_absent"
        )
        driver = RedisStorageDriver(client=faulty_client, key_prefix=KEY_PREFIX)
        payload = make_payload()
        expected_hash = hashlib.sha256(payload.SerializeToString()).hexdigest()
        expected_key = f"{KEY_PREFIX}:v0:d:sha256:{expected_hash}"
        with pytest.raises(RuntimeError) as exc_info:
            await driver.store(make_store_context(), [payload])
        assert str(exc_info.value) == f"RedisStorageDriver store failed [key={expected_key}]"
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    async def test_retrieve_client_failure_raises(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        [claim] = await driver.store(make_store_context(), [make_payload("value")])

        faulty_client = FailOnceDriverClient(delegate=driver_client, fail_on="get")
        driver = RedisStorageDriver(client=faulty_client, key_prefix=KEY_PREFIX)
        with pytest.raises(RuntimeError) as exc_info:
            await driver.retrieve(StorageDriverRetrieveContext(), [claim])
        assert (
            str(exc_info.value)
            == f"RedisStorageDriver retrieve failed [key={claim.claim_data['key']}]"
        )
        assert isinstance(exc_info.value.__cause__, ConnectionError)


class TestRedisStorageDriverConcurrency:
    async def test_store_payloads_concurrently(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        num_payloads = 5
        barrier = _AsyncBarrier(num_payloads)
        driver_client.set_if_absent = _barrier_wrapper(  # type: ignore[method-assign]
            driver_client.set_if_absent,
            barrier,
        )

        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payloads = [make_payload(f"concurrent-store-{i}") for i in range(num_payloads)]

        claims = await driver.store(make_store_context(), payloads)
        assert len(claims) == num_payloads

    async def test_retrieve_payloads_concurrently(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        num_payloads = 5
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payloads = [make_payload(f"concurrent-retrieve-{i}") for i in range(num_payloads)]
        claims = await driver.store(make_store_context(), payloads)

        barrier = _AsyncBarrier(num_payloads)
        driver_client.get = _barrier_wrapper(driver_client.get, barrier)  # type: ignore[method-assign]

        retrieved = await driver.retrieve(StorageDriverRetrieveContext(), claims)
        assert retrieved == payloads

    async def test_store_cancels_remaining_on_failure(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        faulty_client = FailOnceDriverClient(
            delegate=driver_client,
            fail_on="set_if_absent",
        )
        driver = RedisStorageDriver(client=faulty_client, key_prefix=KEY_PREFIX)
        payloads = [make_payload(f"cancel-store-{i}") for i in range(3)]

        with pytest.raises(
            RuntimeError,
            match=r"RedisStorageDriver store failed \[key=.+\]",
        ) as exc_info:
            await driver.store(make_store_context(), payloads)

        assert isinstance(exc_info.value.__cause__, ConnectionError)
        assert str(exc_info.value.__cause__) == "Redis connection lost"
        assert (
            len(faulty_client.cancelled) == 2
        ), "Expected 2 remaining tasks to be cancelled"

    async def test_retrieve_cancels_remaining_on_failure(
        self, driver_client: RedisStorageDriverClient
    ) -> None:
        driver = RedisStorageDriver(client=driver_client, key_prefix=KEY_PREFIX)
        payloads = [make_payload(f"cancel-retrieve-{i}") for i in range(3)]
        claims = await driver.store(make_store_context(), payloads)

        faulty_client = FailOnceDriverClient(delegate=driver_client, fail_on="get")
        driver = RedisStorageDriver(client=faulty_client, key_prefix=KEY_PREFIX)

        with pytest.raises(
            RuntimeError,
            match=r"RedisStorageDriver retrieve failed \[key=.+\]",
        ) as exc_info:
            await driver.retrieve(StorageDriverRetrieveContext(), claims)

        assert isinstance(exc_info.value.__cause__, ConnectionError)
        assert str(exc_info.value.__cause__) == "Redis connection lost"
        assert (
            len(faulty_client.cancelled) == 2
        ), "Expected 2 remaining tasks to be cancelled"
