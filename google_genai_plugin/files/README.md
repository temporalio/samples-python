# Files

Upload a file with the Gemini Files API, then ask the model about it.
`client.files.upload` runs as a Temporal activity on the worker (the file is
read there), and the returned file handle is referenced in a `generate_content`
call.

> **Requires a live Gemini API key.** The Files API talks to a real backend that
> the plugin's test server does not mock, so this sample has no automated test —
> run it against a real `GOOGLE_API_KEY`. The file path is resolved on the
> worker, so `sample.txt` must be reachable by the worker process.

## What This Sample Demonstrates

- `client.files.upload(file=..., config=UploadFileConfig(...))` as a durable activity
- Referencing the uploaded file handle in `generate_content` `contents`

## Running the Sample

Prerequisites: install dependencies, set `GOOGLE_API_KEY`, and start a Temporal
dev server. See the [suite README](../README.md).

```bash
# Terminal 1
uv run google_genai_plugin/files/run_worker.py

# Terminal 2
uv run google_genai_plugin/files/run_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `sample.txt` | The document uploaded and summarized |
| `workflow.py` | `FilesWorkflow` — uploads a file, then summarizes it |
| `run_worker.py` | Registers `GoogleGenAIPlugin`, starts the worker |
| `run_workflow.py` | Executes the workflow with the sample file path |
