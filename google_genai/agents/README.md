# Managed Agents

Managed agents (`client.agents`) are server-side resources you can create, fetch,
list, and delete. This sample runs the full CRUD cycle, each operation as a
Temporal activity.

> **Requires a live Gemini API key.** The Agents API talks to a real backend that
> the plugin's test server does not mock, so this sample has no automated test —
> run it against a real `GOOGLE_API_KEY`.

## What This Sample Demonstrates

- `client.agents.create(id=..., system_instruction=...)`
- `client.agents.get(id)`, `client.agents.list(page_size=...)`, `client.agents.delete(id)`
- Cleaning up the agent in a `finally` block so a failure mid-cycle doesn't leak it

## Creating Server-Side Resources Durably

Every call here runs as an activity, so each one can be retried — including
after it already succeeded on the backend but its completion was lost. Two
habits worth carrying into real code:

- **Make creates idempotent.** `client.agents.create(id=...)` with a
  caller-chosen id fails with "already exists" on such a retry. Derive the id
  deterministically from workflow state (`workflow.uuid4()`, or the workflow id)
  so every attempt targets the same resource, and treat "already exists" as
  success — for example by falling back to `client.agents.get(id)`.
- **Clean up in a `finally`.** Without it, a failing `get`/`list` skips the
  `delete` and the agent lingers on Google's backend even though the workflow
  ended.

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai/agents/run_worker.py

# Terminal 2
uv run google_genai/agents/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `AgentsWorkflow` — create, get, list, delete a managed agent |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
