# Streaming

Watch Claude's reply appear token by token through a [Workflow Stream](https://docs.temporal.io/develop/python/workflows/workflow-streams) (experimental).

## What this shows

- **Live output, durable Workflow.** Clients see the text as Claude writes it. The Workflow itself still works with complete messages.
- **Watching is optional.** The Workflow doesn't wait for anyone to subscribe, and returns the same result either way.
## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal.

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/streaming/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which answers in five scripted chunks. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

### Start the Workflow with a live subscriber

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/streaming/run_workflow.py
```

The text prints as it arrives, then `Final result:` repeats it. Offline that's `One. Two. Three. Four. Five.`, and the chunks reach you through Claude Code and the Workflow Stream, the same path live tokens take. Pass your own prompt as arguments.

The Temporal CLI can't subscribe to a Workflow Stream, which is why this case has its own script.

### Start the Workflow with no subscriber

```bash
temporal workflow execute \
  --type StreamingWorkflow \
  --task-queue claude-agent-sdk-streaming \
  --workflow-id claude-agent-sdk-streaming-nosub \
  --input '"Count from one to five, one number per sentence."'
```

The Workflow completes with the same result.
