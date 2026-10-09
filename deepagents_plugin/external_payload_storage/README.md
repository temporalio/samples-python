# External Storage

Run a Deep Agent whose `read_file` tool returns **6 MiB** of text, exceeding
Temporal's default 2 MiB payload limit. The SDK's native `ExternalStorage`
offloads the tool output and the next model activity's input to S3, recording
small references in workflow history and retrieving the full bytes on decode.
The workflow returns only a byte count, SHA-256, and a short final answer.

Native External Storage is in **Public Preview**. This sample uses the SDK's
`S3StorageDriver` with the local mock S3 service from the
[general External Storage sample](../../external_storage). Neither AWS credentials,
Docker, nor an LLM API key is needed. The model replies are scripted; the real
Deep Agents loop, tool activity, model activities, and S3 transfers still run.

## Running the sample

Use Python **3.11 or later**. Run these commands from the repository root:

```bash
uv sync --python 3.13 --group deepagents --group external-storage
```

Start Temporal with its default payload limits in one terminal:

```bash
temporal server start-dev
```

In a second terminal, start the existing mock S3 service. It listens on port
5000 and creates the `temporal-payloads` bucket:

```bash
uv run external_storage/s3.py
```

In a third terminal, run the demo. It starts a worker, executes one workflow,
checks the result's integrity, and shuts down the worker:

```bash
uv run deepagents_plugin/external_payload_storage/main.py
```

The output includes:

```text
Tool result: 6,291,456 bytes (6 MiB), integrity verified
Agent: Received the complete document.
```

The script also prints the workflow ID and complete SHA-256. Inspect the history
in the Temporal UI or with:

```bash
temporal workflow show --workflow-id <printed-workflow-id>
```

The completed `deepagents.invoke_tool` activity and the following
`deepagents.invoke_model` input contain native storage references. The first
model input and final workflow result remain small and inline.

To view externally stored payloads in the UI, reuse the
[storage-aware codec server](../../external_storage#5-optional-run-the-codec-server):
run `uv run external_storage/codec_server.py` and set the UI's Remote Codec
Endpoint to `http://localhost:8081`. Its gzip decoder passes uncompressed payloads
through, so it can also read this sample's references.

## How the configuration works

`client.py` creates `ExternalStorage(drivers=[driver],
payload_size_threshold=256 * 1024)`, adds it to the SDK's default converter with
`dataclasses.replace`, and passes that converter into the Deep Agents plugin:

```python
data_converter = replace(DataConverter.default, external_storage=storage)
plugin = DeepAgentsPlugin(data_converter=data_converter)

client = await Client.connect(
    "localhost:7233",
    plugins=[plugin],
)
```

The plugin upgrades the default payload converter for LangChain types while
preserving the converter's external-storage configuration. This uses the
standalone plugin's supported `data_converter` constructor argument.

The worker inherits the configured converter. The S3 client stays open while
the worker runs and the starter decodes results. No application code uploads or
downloads Temporal payloads manually.

This demo deliberately uses **no compression codec**: repeated `x` characters
would compress well below the storage threshold. It overrides the built-in
`read_file` tool with an activity-backed mock bulk reader. Deep Agents excludes
`read_file` from tool-result eviction, so the complete result crosses both
activity boundaries. Applications using real models should page documents or
retrieve excerpts to manage context separately. Storage reduces transport and
history bytes; it does not reduce model tokens or decoded workflow memory.

With storage removed, this tool result fails with `PayloadsTooLarge` at the
default limits. Raising the blob limit alone still leaves the gRPC message
limit described in [Hanyu Liu's post](https://hanyuliu.me/posts/temporal-deep-agent-payload-limits/).
Native storage avoids transmitting the large bytes through either limit.

For real S3, use an existing bucket and normal AWS credentials instead of this
sample's local endpoint and mock credentials. Configure compatible storage
drivers on every client, worker, and replayer that reads the history. Retain
objects for as long as execution, reset, or replay may need them; Temporal does
not delete stored payloads when an activity finishes.

## Tests

The integration test starts an isolated mock S3 service and verifies the full
result, both native references, activity routing, and replay with a new S3
client after worker shutdown.
No manually running S3 service or model credentials are required:

```bash
uv sync --python 3.13 --group deepagents --group external-storage --group dev
uv run pytest tests/deepagents_plugin/external_payload_storage_test.py
```
