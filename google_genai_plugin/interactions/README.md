# Interactions

The Interactions API (`client.interactions`) is a server-managed, stateful
conversation API: state lives on Google's backend, addressed by an interaction
id. This sample creates an interaction, fetches it, and deletes it — each
operation running as a Temporal activity.

> **Requires a live Gemini API key.** The Interactions API talks to a real
> backend that the plugin's test server does not mock, so this sample has no
> automated test — run it against a real `GOOGLE_API_KEY`.

Note: unlike `client.models`, the Interactions API has no automatic function
calling. To use tools, declare them as `{"type": "function", ...}` dicts and
drive the tool loop yourself.

## What This Sample Demonstrates

- `client.interactions.create(model=..., input=...)` as a durable activity
- `client.interactions.get(id)` and `client.interactions.delete(id)`

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/interactions/run_worker.py

# Terminal 2
uv run google_genai_plugin/interactions/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `InteractionsWorkflow` — create, get, delete an interaction |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
