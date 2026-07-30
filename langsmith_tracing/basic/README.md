# Basic LLM Workflow

A one-shot workflow that sends a prompt to OpenAI and returns the response. A very simple example of LangSmith tracing with Temporal.

See the [parent README](../README.md) for prerequisites.

## Running

```bash
# Terminal 1 — start the worker
uv run --group langsmith-tracing python -m langsmith_tracing.basic.worker

# Terminal 2 — run the workflow
uv run --group langsmith-tracing python -m langsmith_tracing.basic.starter
```

## Trace Structure

### `add_temporal_runs=False` (default)

Only `@traceable` and `wrap_openai` spans appear. The client-side `@traceable` is the root, and workflow/activity traces nest under it via context propagation.

```
Basic LLM Request                    (@traceable, client-side)
└── Ask: What is Temporal?           (@traceable, workflow)
    └── Call OpenAI                   (@traceable, activity)
        └── ChatOpenAI                (automatic via wrap_openai)
```

### `add_temporal_runs=True`

Pass `--add-temporal-runs` to both the worker and starter:

```bash
uv run --group langsmith-tracing python -m langsmith_tracing.basic.worker --add-temporal-runs
uv run --group langsmith-tracing python -m langsmith_tracing.basic.starter --add-temporal-runs
```

Temporal operation spans are added. `StartWorkflow`/`RunWorkflow` and `StartActivity`/`RunActivity` appear as sibling pairs:

```
Basic LLM Request                       (@traceable, client-side)
├── StartWorkflow:BasicLLMWorkflow      (automatic, Temporal plugin)
└── RunWorkflow:BasicLLMWorkflow        (automatic, Temporal plugin)
    └── Ask: What is Temporal?          (@traceable, workflow)
        ├── StartActivity:call_openai   (automatic, Temporal plugin)
        └── RunActivity:call_openai     (automatic, Temporal plugin)
            └── Call OpenAI             (@traceable, activity)
                └── ChatOpenAI          (automatic via wrap_openai)
```
