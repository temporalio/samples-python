"""Redis storage driver for Temporal external storage."""

from __future__ import annotations

import asyncio
import hashlib
import urllib.parse
from collections.abc import Coroutine, Sequence
from datetime import timedelta
from typing import Any, TypeVar

from temporalio.api.common.v1 import Payload
from temporalio.converter import (
    StorageDriver,
    StorageDriverActivityInfo,
    StorageDriverClaim,
    StorageDriverRetrieveContext,
    StorageDriverStoreContext,
    StorageDriverWorkflowInfo,
)
from temporalio.exceptions import ApplicationError

from external_storage_redis._client import RedisStorageDriverClient

_T = TypeVar("_T")


async def _gather_with_cancellation(
    coros: Sequence[Coroutine[Any, Any, _T]],
) -> list[_T]:
    """Run coroutines concurrently, cancelling remaining tasks on failure."""
    if not coros:
        return []
    tasks = [asyncio.create_task(coro) for coro in coros]
    try:
        return list(await asyncio.gather(*tasks))
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


class RedisStorageDriver(StorageDriver):
    """Driver for storing and retrieving Temporal payloads in Redis.

    Payloads are stored as Redis string values keyed by a SHA-256 digest of the
    serialized payload bytes. The key also includes namespace and
    workflow/activity identity segments derived from the storage context so
    distinct Temporal scopes remain isolated.
    """

    def __init__(
        self,
        client: RedisStorageDriverClient,
        *,
        driver_name: str = "redis",
        key_prefix: str = "temporalio:payloads",
        ttl: timedelta | None = None,
        max_payload_size: int = 50 * 1024 * 1024,
    ) -> None:
        """Construct the Redis driver.

        Args:
            client: A :class:`RedisStorageDriverClient` implementation. Use
                :func:`external_storage_redis.redis_asyncio.new_redis_asyncio_client`
                to wrap a ``redis.asyncio`` client.
            driver_name: Name of this driver instance. Defaults to ``"redis"``.
                Override this when registering multiple RedisStorageDriver
                instances with distinct configurations under the same
                ``ExternalStorage.drivers`` list.
            key_prefix: Prefix prepended to all Redis keys. Defaults to
                ``"temporalio:payloads"``.
            ttl: Optional expiration to apply when a key is first written.
                Existing keys are not refreshed when the same payload is stored
                again.
            max_payload_size: Maximum serialized payload size in bytes that the
                driver will accept. Defaults to 52428800 (50 MiB).
        """
        if max_payload_size <= 0:
            raise ValueError("max_payload_size must be greater than zero")
        if ttl is not None and ttl <= timedelta(0):
            raise ValueError("ttl must be greater than zero")
        self._client = client
        self._driver_name = driver_name or "redis"
        self._key_prefix = key_prefix.rstrip(":")
        self._ttl = ttl
        self._max_payload_size = max_payload_size

    def name(self) -> str:
        """Return the driver instance name."""
        return self._driver_name

    def type(self) -> str:
        """Return the driver type identifier."""
        return "redis"

    def _build_key(
        self,
        context: StorageDriverStoreContext,
        hash_digest: str,
    ) -> str:
        """Construct a context-aware Redis key for a payload digest."""

        def _quote(value: str | None) -> str | None:
            return urllib.parse.quote(value, safe="") if value else None

        segments = ["v0"]
        target = context.target
        namespace = _quote(target.namespace) if target is not None else None
        if namespace:
            segments.extend(["ns", namespace])

        if isinstance(target, StorageDriverWorkflowInfo):
            segments.extend(
                [
                    "wt",
                    _quote(target.type) or "null",
                    "wi",
                    _quote(target.id) or "null",
                    "ri",
                    _quote(target.run_id) or "null",
                ]
            )
        elif isinstance(target, StorageDriverActivityInfo):
            segments.extend(
                [
                    "at",
                    _quote(target.type) or "null",
                    "ai",
                    _quote(target.id) or "null",
                    "ri",
                    _quote(target.run_id) or "null",
                ]
            )

        segments.extend(["d", "sha256", hash_digest])
        if not self._key_prefix:
            return ":".join(segments)
        return f"{self._key_prefix}:{':'.join(segments)}"

    async def store(
        self,
        context: StorageDriverStoreContext,
        payloads: Sequence[Payload],
    ) -> list[StorageDriverClaim]:
        """Store payloads in Redis and return a claim for each payload."""

        async def _store_payload(payload: Payload) -> StorageDriverClaim:
            payload_bytes = payload.SerializeToString()
            payload_size = len(payload_bytes)
            if payload_size > self._max_payload_size:
                raise ValueError(
                    f"Payload size {payload_size} bytes exceeds the configured "
                    f"max_payload_size of {self._max_payload_size} bytes"
                )

            hash_digest = hashlib.sha256(payload_bytes).hexdigest().lower()
            key = self._build_key(context, hash_digest)

            try:
                await self._client.set_if_absent(
                    key=key,
                    data=payload_bytes,
                    ttl=self._ttl,
                )
            except Exception as err:
                raise RuntimeError(
                    f"RedisStorageDriver store failed [key={key}]"
                ) from err

            return StorageDriverClaim(
                claim_data={
                    "key": key,
                    "hash_algorithm": "sha256",
                    "hash_value": hash_digest,
                },
            )

        return await _gather_with_cancellation([_store_payload(p) for p in payloads])

    async def retrieve(
        self,
        context: StorageDriverRetrieveContext,  # noqa: ARG002
        claims: Sequence[StorageDriverClaim],
    ) -> list[Payload]:
        """Retrieve payloads from Redis for the given claims."""

        async def _retrieve_payload(claim: StorageDriverClaim) -> Payload:
            key = claim.claim_data["key"]

            try:
                payload_bytes = await self._client.get(key=key)
            except Exception as err:
                raise RuntimeError(
                    f"RedisStorageDriver retrieve failed [key={key}]"
                ) from err

            if payload_bytes is None:
                raise ApplicationError(
                    f"Payload not found for key '{key}'",
                    type="PayloadNotFoundError",
                    non_retryable=True,
                )

            expected_hash = claim.claim_data.get("hash_value")
            hash_algorithm = claim.claim_data.get("hash_algorithm")
            if expected_hash and hash_algorithm:
                if hash_algorithm != "sha256":
                    raise ValueError(
                        f"RedisStorageDriver unsupported hash algorithm "
                        f"[key={key}]: expected sha256, got {hash_algorithm}"
                    )
                actual_hash = hashlib.sha256(payload_bytes).hexdigest().lower()
                if actual_hash != expected_hash:
                    raise ValueError(
                        f"RedisStorageDriver integrity check failed "
                        f"[key={key}]: expected {hash_algorithm}:{expected_hash}, "
                        f"got {hash_algorithm}:{actual_hash}"
                    )

            payload = Payload()
            payload.ParseFromString(payload_bytes)
            return payload

        return await _gather_with_cancellation(
            [_retrieve_payload(claim) for claim in claims]
        )
