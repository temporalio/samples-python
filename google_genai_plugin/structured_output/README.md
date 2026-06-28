# Structured Output

Get typed JSON back from Gemini by passing a Pydantic model as `response_schema`.
The plugin installs a `PydanticPayloadConverter`, so the model serializes cleanly
through Temporal payloads — the workflow returns a real `Recipe` instance.

## What This Sample Demonstrates

- `GenerateContentConfig(response_mime_type="application/json", response_schema=Recipe)`
- Reading the parsed model from `response.parsed`
- Returning a Pydantic model as a workflow result via the plugin's Pydantic converter

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/structured_output/run_worker.py

# Terminal 2
uv run google_genai_plugin/structured_output/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | The `Recipe` model and `StructuredOutputWorkflow` |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow and prints the typed recipe |
