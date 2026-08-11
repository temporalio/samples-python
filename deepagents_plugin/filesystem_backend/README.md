# Filesystem Backend

Give a Deep Agent durable, real filesystem access. The agent's built-in file
tools (`write_file`, `read_file`, `ls`, …) delegate to a *backend*. Wrapping a
`FilesystemBackend` with `TemporalBackend(inner, activity_options=...)` routes
each file operation through a `deepagents.backend_op` activity, so real disk I/O
happens in an activity worker instead of in workflow code.

Contrast this with the default `StateBackend`, whose "files" live in agent state
— that is pure workflow state and correctly stays in the workflow with no
wrapping. `TemporalBackend` is only for backends that do real I/O.

The scratch directory (`root_dir`) is chosen client-side and passed in as a
workflow argument, so the workflow never reads the environment or the disk
directly.

## What This Sample Demonstrates

- `TemporalBackend` wrapping a real-I/O `FilesystemBackend`
- The agent's built-in file tools running their I/O as `backend_op` activities
- Keeping the workflow deterministic by passing `root_dir` in as an argument

## Running the Sample

Prerequisites: Python >= 3.11 with the [suite setup](../README.md#prerequisites)
applied (interim plugin install), an `ANTHROPIC_API_KEY` in your
environment, and a running Temporal dev server (`temporal server start-dev`).

> The experimental plugin is not in the `deepagents` group — install it as shown
> in the [suite README](../README.md#prerequisites) and run with `--no-sync`, or
> a bare `uv run`/`uv sync` re-syncs the environment and uninstalls it.

```bash
# Terminal 1
uv run --no-sync deepagents_plugin/filesystem_backend/run_worker.py

# Terminal 2
uv run --no-sync deepagents_plugin/filesystem_backend/run_workflow.py
```

By default the starter creates a temporary scratch directory; set
`DEEPAGENTS_WORKDIR` to point the agent at a directory of your choice.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `FilesystemAgent` wrapping a `FilesystemBackend` in `TemporalBackend` |
| `run_worker.py` | Adds `DeepAgentsPlugin`, starts the worker |
| `run_workflow.py` | Chooses a scratch dir, executes the workflow, prints the result |
