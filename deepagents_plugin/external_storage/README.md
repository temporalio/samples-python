# External Storage

This sample runs a Deep Agent whose activity-backed `read_file` tool returns a
**6 MiB** document. Temporal's native `ExternalStorage` stores the tool result
and the following model activity input in S3, leaving small references in
workflow history. The workflow returns only the document's byte count, SHA-256,
and final answer.

The client configures `ExternalStorage` on a data converter and passes it to
`DeepAgentsPlugin`, which composes it with its LangChain-aware converter. The
worker inherits that configuration. Payloads above the default **256 KiB**
threshold are uploaded and downloaded automatically; the workflow input, first
model input, and final result stay inline. The agent loop runs in the workflow,
and each model and tool call runs as its own plugin activity.

The S3 driver uses the local mock service from the
[general External Storage sample](../../external_storage). No AWS credentials,
Docker, or LLM API key is needed. The model replies are scripted; the real Deep
Agents loop, tool activity, model activities, and S3 transfers still run.

## Run it

Use Python **3.11 or later**:

```bash
uv sync --python 3.13 --group deepagents --group external-storage
```

Start Temporal in one terminal:

```bash
temporal server start-dev
```

Start the mock S3 service in another terminal. It listens on port 5000 and
creates the `temporal-payloads` bucket:

```bash
uv run external_storage/s3.py
```

Run the demo:

```bash
uv run deepagents_plugin/external_storage/main.py
```

The output includes the workflow ID, verified document size and SHA-256, and
final answer. Inspect the workflow history with:

```bash
temporal workflow show --workflow-id <printed-workflow-id>
```

Activity inputs and results above the threshold appear as native storage
references. To view externally stored payloads in the UI, run the
[storage-aware codec server](../../external_storage#5-optional-run-the-codec-server)
and set the UI's Remote Codec Endpoint to `http://localhost:8081`.

For real S3, use an existing bucket and normal AWS credentials. Configure
compatible storage drivers on every client, worker, and replayer that reads the
history. Keep payload objects for as long as execution, reset, or replay may
need them. The local mock S3 service is in memory.
