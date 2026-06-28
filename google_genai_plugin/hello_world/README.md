# Hello World

The simplest Google GenAI + Temporal sample: one `generate_content` call. The
call runs as a Temporal activity, so it gets durable retries, timeouts, and
crash recovery, and the Gemini credentials never enter the workflow.

## What This Sample Demonstrates

- Wiring `GoogleGenAIPlugin` onto the worker with a real `genai.Client`
- Constructing a `TemporalAsyncClient` inside a `@workflow.defn`
- Calling `client.models.generate_content(...)` durably

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server (`temporal server start-dev`). See the
[suite README](../README.md) for details.

```bash
# Terminal 1
uv run google_genai_plugin/hello_world/run_worker.py

# Terminal 2
uv run google_genai_plugin/hello_world/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `HelloWorldWorkflow` with a single `generate_content` call |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
