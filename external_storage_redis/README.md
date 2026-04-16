# Redis External Storage

This sample packages a Redis-backed `StorageDriver` implementation for Temporal
external storage.

The code lives in:

* `external_storage_redis/_driver.py` for the `RedisStorageDriver`
* `external_storage_redis/_client.py` for the storage client abstraction
* `external_storage_redis/redis_asyncio.py` for the `redis.asyncio` adapter
* `tests/external_storage_redis/` for unit and worker integration tests

Unlike most samples in this repository, this one is primarily reusable driver
code plus tests rather than a standalone `worker.py` / `starter.py` pair.

## Install Dependencies

From the repository root:

    uv sync --group external-storage-redis --group dev

The `external-storage-redis` group installs `redis`, and the `dev` group
installs `fakeredis` for the test suite.

## Using The Driver

```python
import dataclasses

import redis.asyncio as redis
import temporalio.converter
from temporalio.client import Client
from temporalio.converter import ExternalStorage

from external_storage_redis import RedisStorageDriver
from external_storage_redis.redis_asyncio import new_redis_asyncio_client

redis_client = redis.Redis.from_url(
    "redis://localhost:6379/0",
    decode_responses=False,
)
try:
    driver = RedisStorageDriver(
        client=new_redis_asyncio_client(redis_client),
        key_prefix="temporalio:payloads",
    )

    client = await Client.connect(
        "localhost:7233",
        data_converter=dataclasses.replace(
            temporalio.converter.default(),
            external_storage=ExternalStorage(
                drivers=[driver],
                payload_size_threshold=256 * 1024,
            ),
        ),
    )
finally:
    await redis_client.aclose()
```

`decode_responses=False` is required because the driver stores serialized
Temporal `Payload` protobuf bytes as Redis values rather than text.

## Driver Behavior

`RedisStorageDriver` accepts these constructor options:

* `driver_name`: defaults to `"redis"`
* `key_prefix`: defaults to `"temporalio:payloads"`
* `ttl`: optional expiration applied only when a key is first inserted
* `max_payload_size`: defaults to 50 MiB

Stored keys are content-addressed using SHA-256 and include Temporal execution
context when it is available. A typical workflow-scoped key looks like:

    temporalio:payloads:v0:ns:default:wt:MyWorkflow:wi:my-workflow-id:ri:my-run-id:d:sha256:<hash>

Some behavior to be aware of:

* Any driver used to store payloads must also be configured on the component
  that retrieves them.
* The Redis instance must already exist; the driver does not provision it.
* Identical serialized bytes within the same namespace and workflow/activity
  scope share the same Redis key.
* Workflow, activity, namespace, and run identifiers are URL-encoded before
  being placed into the key.
* Only payloads at or above `ExternalStorage.payload_size_threshold` are
  offloaded.
* If `ttl` is set, duplicate stores do not refresh expiration.
* If a payload key is missing at retrieval time, the driver raises a
  non-retryable `ApplicationError`.

## Custom Redis Clients

To use a Redis library other than `redis.asyncio`, implement
`RedisStorageDriverClient`:

```python
from datetime import timedelta

from external_storage_redis import RedisStorageDriverClient


class MyRedisClient(RedisStorageDriverClient):
    async def get(self, *, key: str) -> bytes | None: ...

    async def set_if_absent(
        self,
        *,
        key: str,
        data: bytes,
        ttl: timedelta | None = None,
    ) -> bool: ...
```

## Tests

Run the full Redis sample test suite with:

    uv run pytest tests/external_storage_redis

Run only the in-memory unit tests with:

    uv run pytest tests/external_storage_redis/test_redis.py

The worker integration tests use `WorkflowEnvironment.start_local()` and
`fakeredis`. They do not require a real Redis server, but the first run may
download a Temporal dev-server binary.

Some Temporal dev-server builds disable standalone activity execution. When
that happens, the two standalone-activity integration tests skip automatically.
