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

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/agents/run_worker.py

# Terminal 2
uv run google_genai_plugin/agents/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `AgentsWorkflow` — create, get, list, delete a managed agent |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
