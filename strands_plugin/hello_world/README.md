# Hello World

The simplest Strands + Temporal sample: one `TemporalAgent` invoked once. Every model call runs as an `invoke_model` Temporal activity, so it gets durable retries, timeouts, and crash recovery for free.

## What This Sample Demonstrates

- Wiring `StrandsPlugin` onto the client and worker
- Constructing a `TemporalAgent` with no explicit model (defaults to `BedrockModel()`)
- Invoking the agent from a `@workflow.defn`

## Running the Sample

Prerequisites: `uv sync --group strands`, AWS credentials with Bedrock access, and a running Temporal dev server (`temporal server start-dev`).

```bash
# Terminal 1
uv run strands_plugin/hello_world/run_worker.py

# Terminal 2
uv run strands_plugin/hello_world/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `HelloWorldWorkflow` with a single `TemporalAgent` |
| `run_worker.py` | Registers `StrandsPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the result |
