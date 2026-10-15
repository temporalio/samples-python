# External Storage

This sample uses S3 for two purposes:

* A Deep Agent tool returns a **6 MiB** document. The tool result and the next
  model activity input are stored in S3, with small references in workflow
  history.
* The complete conversation is retained as **one immutable JSON object per
  message**, including assistant tool calls and the full tool result. Each new
  user turn passes a conversation ID, message offset, and the new question;
  earlier turns are loaded inside the model activity.

The workflow creates one agent and reuses it for every question. Each invocation
puts the conversation ID and message offset in the user message's
`additional_kwargs`. The plugin's `model_provider` returns the small worker-side
wrapper in `storage.py`, which reads that reference inside the model activity.
The agent loop stays in the workflow, and each model and tool call still runs as
its own plugin activity. No custom activity or Deep Agents backend is needed.

Transcript objects live under `conversations/<conversation-id>/<index>.json`.
Conditional S3 writes preserve existing messages and let a retried model call
reuse its committed reply, even after later turns have been added. One workflow
owns each conversation. System instructions remain model configuration, rather
than conversation messages.

Only the latest **16 messages** are loaded as model context; older messages stay
in S3. This keeps both transcript storage and cumulative context reads linear in
the conversation's total bytes for this fixed window. Retaining every message
does not require sending every message to every model call. A production agent
can add token-based budgeting, summaries, or retrieval for older details.

Temporal's separate `ExternalStorage` configuration uses its default 256 KiB
threshold. It offloads the large tool result and the following model activity
input. Ordinary conversation inputs stay small and inline, instead of saving a
new full-transcript snapshot on every turn.

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

The output includes the workflow ID, document size, transcript S3 prefix and
message count, and final answer. Inspect the workflow history with:

```bash
temporal workflow show --workflow-id <printed-workflow-id>
```

Activity inputs and results above the threshold appear as native storage
references. To view externally stored payloads in the UI, run the
[storage-aware codec server](../../external_storage#5-optional-run-the-codec-server)
and set the UI's Remote Codec Endpoint to `http://localhost:8081`.

For real S3, use an existing bucket and normal AWS credentials. Configure
compatible storage drivers on every client, worker, and replayer that reads the
history. Keep Temporal payload objects for as long as execution, reset, or replay
may need them, and keep transcript objects for the application's conversation
retention period. The local mock S3 service is in memory.
