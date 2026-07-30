# Structured Output

`TemporalAgent` accepts a `structured_output_model=` Pydantic class and returns the agent's response coerced into that model. The plugin installs Temporal's `pydantic_data_converter` by default, so the typed value serializes cleanly across the activity and workflow boundary.

## What This Sample Demonstrates

- `TemporalAgent(structured_output_model=PersonInfo, ...)`
- Pulling `result.structured_output` out of the agent result
- The plugin's auto-configured pydantic data converter — no extra setup needed to ship Pydantic types in workflow inputs/outputs

## Running the Sample

```bash
# Terminal 1
uv run strands_plugin/structured_output/run_worker.py

# Terminal 2
uv run strands_plugin/structured_output/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `PersonInfo` model and `StructuredOutputWorkflow` |
| `run_worker.py` | Registers `StrandsPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the typed result |
