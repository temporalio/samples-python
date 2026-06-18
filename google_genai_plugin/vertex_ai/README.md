# Vertex AI

The same hello-world flow as [`hello_world`](../hello_world), but pointed at
**Vertex AI** instead of the Gemini Developer API. The only difference is
configuration: both the worker's `genai.Client` and the workflow's
`TemporalAsyncClient` set `vertexai=True` with a Google Cloud project and
location. The `vertexai` setting must match on both sides.

> **Requires Google Cloud credentials**, not a Gemini API key. Authenticate with
> Application Default Credentials (`gcloud auth application-default login`) or a
> service-account key (`GOOGLE_APPLICATION_CREDENTIALS`). This sample has no
> automated test.

## Configuration

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Your Google Cloud project ID (required) |
| `GOOGLE_CLOUD_LOCATION` | Region, e.g. `us-central1` (defaults to `us-central1`) |

## What This Sample Demonstrates

- `genai.Client(vertexai=True, project=..., location=...)` on the worker
- `TemporalAsyncClient(vertexai=True, project=..., location=...)` in the workflow
- Passing project/location as workflow arguments to keep the workflow deterministic

## Running the Sample

Prerequisites: install dependencies, configure GCP credentials, set
`GOOGLE_CLOUD_PROJECT`, and start a Temporal dev server. See the
[suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/vertex_ai/run_worker.py

# Terminal 2
uv run google_genai_plugin/vertex_ai/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `VertexAIWorkflow` — generate_content via Vertex AI |
| `run_worker.py` | Registers a Vertex-configured `GoogleGenAIPlugin` |
| `run_workflow.py` | Reads project/location from env and executes the workflow |
