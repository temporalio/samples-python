# Structured Output

Constrain Claude Code's final answer to a JSON schema and validate it as a typed Pydantic model at the Workflow boundary.

## What this shows

- **Typed results from an agent.** You define a Pydantic model, and the Workflow returns an instance of it instead of free text.
- **Claude fixes its own mistakes.** Claude Code checks the answer against the schema and sends errors back to the model, so it can try again.
- **A clear failure.** If no valid answer ever comes, the Workflow fails instead of returning bad data.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start the Worker in another terminal.

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/structured_output/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which answers with a fixed ticket. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

Triage a message from a third terminal:

```bash
temporal workflow execute \
  --type TriageTicketWorkflow \
  --task-queue claude-agent-sdk-structured-output \
  --workflow-id structured-output \
  --input '"The app crashes every time I open the settings page."'
```

## Expected behavior

The result is the typed ticket as JSON, for example `{"category": "bug", "priority": 2, "summary": "..."}`. Offline it is always:

```json
{"category": "bug", "priority": 2, "summary": "The settings page crashes the app when opened."}
```

Offline, the ticket's values are scripted, but Claude Code still checks them against the schema and the Workflow still validates them as a `SupportTicket`.
