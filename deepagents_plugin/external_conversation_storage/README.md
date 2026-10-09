# External Storage and Conversation History

This companion demonstrates the same native S3 payload configuration pattern as
[external_payload_storage](../external_payload_storage), but has its own client
setup and can be run independently. It runs a four-turn conversation. It writes
each user/assistant exchange to a separate S3 object, then loads every previous
exchange for each model call. The full transcript is available to the agent
throughout the conversation.

The S3 transcript is application-managed conversation memory. Temporal's native
`ExternalStorage` is configured too, so large workflow and activity payloads can
be stored as S3 references in Temporal history. These solve different problems:
the transcript design makes the full history available to the model, while
native External Storage bounds payload bytes in Temporal history and transport.
The scripted run uses small prompts, so it does not need to cross the native
storage threshold. The full-history approach increases model input size on every
turn; total tokens across a long conversation can grow roughly quadratically.

External storage preserves and retrieves the transcript; it does not reduce
model tokens. For long conversations, a summary or selective retrieval strategy
can keep the model context smaller while still drawing on older turns.

## Run it

Use Python 3.11 or later. Install dependencies:

```bash
uv sync --python 3.13 --group deepagents --group external-storage
```

Start the Temporal dev server in one terminal:

```bash
temporal server start-dev
```

Start the repository's mock S3 service in another terminal:

```bash
uv run external_storage/s3.py
```

Then run the sample:

```bash
uv run deepagents_plugin/external_conversation_storage/main.py
```

It uses a scripted model and needs no provider API key. Each turn's full exchange
is stored under a workflow-specific S3 prefix. The final turn demonstrates that
the complete history carries earlier project details into the answer.

The sample uses the same `temporal-payloads` bucket and local mock S3 service as
the [large-payload sample](../external_payload_storage), but shares no code with
it.
For production, use durable storage with access controls and retention
appropriate for conversation data.
Keep the storage driver configured on clients, workers, and replayers that need
to decode native Temporal payload references.
