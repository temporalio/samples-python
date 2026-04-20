# Basic LLM Workflow

A one-shot workflow that sends a prompt to OpenAI and returns the response. A very simple example of LangSmith tracing with Temporal.

See the [parent README](../README.md) for prerequisites.

## Running

```bash
# Terminal 1 — start the worker
python -m langsmith_tracing.basic.worker

# Terminal 2 — run the workflow
python -m langsmith_tracing.basic.starter
```

## Trace Structure

### `add_temporal_runs=False` (default)

```
Basic LLM Request                    (@traceable, client-side)
└── Ask: What is Temporal?           (@traceable, workflow)
    └── Call OpenAI                   (@traceable, activity)
        └── openai.responses.create   (automatic via wrap_openai)
```

<!-- TODO: Add screenshot of LangSmith trace with add_temporal_runs=False -->

### `add_temporal_runs=True`

Pass `--temporal-runs` to both the worker and starter:

```bash
python -m langsmith_tracing.basic.worker --temporal-runs
python -m langsmith_tracing.basic.starter --temporal-runs
```

```
Basic LLM Request                         (@traceable, client-side)
└── StartWorkflow:BasicLLMWorkflow        (automatic, Temporal plugin)
    └── RunWorkflow:BasicLLMWorkflow      (automatic, Temporal plugin)
        └── Ask: What is Temporal?        (@traceable, workflow)
            └── ExecuteActivity:call_openai  (automatic, Temporal plugin)
                └── Call OpenAI           (@traceable, activity)
                    └── openai.responses.create  (automatic via wrap_openai)
```

<!-- TODO: Add screenshot of LangSmith trace with add_temporal_runs=True showing the additional Temporal operation spans -->
