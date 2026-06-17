# External Storage Sample

This sample demonstrates how to offload large workflow payloads to Amazon S3-compatible
object storage using the Temporal Python SDK's built-in `ExternalStorage` system,
combined with a gzip `PayloadCodec` so the payloads stored inline in Temporal and in
S3 are both compressed.

**Scenario:** A fulfillment center processes batches of shipping orders. The workflow
receives a small request (a batch ID and order count), then internally calls a
`fetch_orders` activity that returns the full list of orders with customer records,
line items, and handling notes. That list — several hundred kilobytes even after
compression — is passed to a second `process_orders` activity. Finally the workflow
returns a small `BatchSummary` with totals.

Each payload is first compressed by `CompressionCodec`. The SDK then checks the
compressed size against the default 256 KiB threshold; payloads still above it are
stored in S3 and replaced inline with compact claim-check references. The workflow's
own input (`OrderBatchRequest`) and result (`BatchSummary`) compress to a few hundred
bytes and remain inline.

A mock S3 service (`s3.py`) is included so you can run the sample locally without
an AWS account or Docker. A `codec_server.py` is included to decompress payloads
on demand for the Temporal Web UI.

## Prerequisites

* [uv](https://docs.astral.sh/uv/)
* [Temporal CLI](https://docs.temporal.io/cli#install) with a local dev server running:
  ```
  temporal server start-dev
  ```

## 1. Sync dependencies

```bash
uv sync --group external-storage
```

## 2. Start the mock S3 service

In a dedicated terminal:

```bash
uv run external_storage/s3.py
```

This starts a local S3-compatible server on port 5000 and creates the `temporal-payloads`
bucket. Leave it running for the duration of the sample.

## 3. Run the worker

In a second terminal:

```bash
uv run external_storage/worker.py
```

## 4. Run the starter

In a third terminal:

```bash
uv run external_storage/starter.py
```

Example output:

```
Starting workflow external-storage-20260501-120000 (batch_id=BATCH-20260501-120000, order_count=200)

Batch BATCH-20260501-120000: 200 orders processed
  Total shipping cost: $28,512.40
  Total weight:        19,684.2 kg
  Avg delivery:        4.4 days
```

## 5. (Optional) Run the codec server

Workflow payloads are gzip-compressed; the large ones additionally live in S3 as
external storage references. The codec server serves both transformations on demand
for the Temporal Web UI. Run it in a fourth terminal:

```bash
uv run external_storage/codec_server.py
```

In the Temporal Web UI (http://localhost:8233), open Settings → Data Encoder and set
the Remote Codec Endpoint to `http://localhost:8081`. Reload the workflow page and the
inline compressed payloads will be displayed as readable JSON, and externally-stored
payloads can be downloaded to fetch their actual content from S3.

The Web UI sends the namespace as the `X-Namespace` header on each request, so
multi-namespace setups can dispatch by reading that header.

| Endpoint | Behavior |
| --- | --- |
| `POST /encode` | Compress the payload, then offload to S3 if it exceeds the threshold. |
| `POST /decode` | Retrieve any external storage references from S3, then decompress. Pass `?preserveStorageRefs=true` to leave references as-is. |
| `POST /download` | All inputs must be storage references. Retrieves them from S3 and decompresses. |

## 6. Inspect the workflow

Run `temporal workflow show` to see how payloads are stored:

```bash
temporal workflow show --workflow-id external-storage-<timestamp>
```

The workflow's input (`OrderBatchRequest`) and result (`BatchSummary`) are gzip-encoded
and stored inline in Temporal — small enough to compress to a few hundred bytes. The
two activity payloads carrying the order list — the output of `fetch_orders` and the
input to `process_orders` — exceed 256 KiB even after compression, so they appear as
external storage references, confirming the SDK offloaded them to S3.

## How it works

The `DataConverter` is configured with both a `payload_codec` and an `external_storage`:

```python
driver = S3StorageDriver(
    client=new_aioboto3_client(s3_client),
    bucket=S3_BUCKET,
)
data_converter = dataclasses.replace(
    temporalio.converter.default(),
    payload_codec=CompressionCodec(),
    external_storage=ExternalStorage(drivers=[driver]),
)
```

On the encode path the SDK:

1. Serializes the Python value to a `Payload`.
2. Runs `CompressionCodec.encode` to gzip the payload bytes.
3. Checks the compressed size against `payload_size_threshold` (default: 256 KiB).
4. If still above the threshold, stores the compressed bytes in S3 via
   `S3StorageDriver` and replaces the inline payload with a claim-check reference.

On the decode path the SDK reverses these steps, transparently retrieving from S3 and
decompressing as needed.

Both the worker and the starter must use the **same** `DataConverter` configuration
(codec **and** storage) so each side can read what the other wrote.
