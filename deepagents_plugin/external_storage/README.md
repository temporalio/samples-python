# External Storage

This sample combines two cases for Temporal's native `ExternalStorage` data
converter:

* A Deep Agent tool returns a **6 MiB** document. The tool result and the next
  model activity input are stored in S3, with small references in workflow
  history.
* The workflow carries a multi-turn conversation. Each model call receives the
  earlier turns as context. The same converter externalizes those activity
  payloads when they exceed the configured threshold.

The sample does not use a DeepAgents backend or manage conversation objects
itself. Temporal's converter externalizes large serialized payloads; it is not
a key-value conversation store. Small conversation state is reconstructed by
workflow replay, while large activity payloads are stored by the configured
S3 driver. The demo threshold is deliberately low (128 bytes) so conversation
payloads also exercise the converter. In a real application, choose a threshold
appropriate for your payloads.

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

The output includes the workflow ID, verified document size and SHA-256, number
of conversation turns, and final answer. Inspect the workflow history with:

```bash
temporal workflow show --workflow-id <printed-workflow-id>
```

Activity inputs and results above the threshold appear as native storage
references. To view externally stored payloads in the UI, run the
[storage-aware codec server](../../external_storage#5-optional-run-the-codec-server)
and set the UI's Remote Codec Endpoint to `http://localhost:8081`.

The client configures `ExternalStorage` on the SDK's default data converter and
passes that converter to `DeepAgentsPlugin`. The worker inherits the converter;
application code does not manually upload or download Temporal payloads. For
real S3, use an existing bucket and normal AWS credentials. Configure compatible
storage drivers on every client, worker, and replayer that reads the history,
and retain objects for as long as execution, reset, or replay may need them.

External Storage reduces bytes in Temporal history and transport. It does not
reduce the number of history events, the model context size, or the total number
of externally stored bytes. Carrying the full transcript into each model call
still increases total conversation payload storage over time.
