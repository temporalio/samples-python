# ⚠️ ANTI-PATTERN: spans from workflow code, sandbox disabled

**This variant is deliberately broken. Do not copy it.** It exists to
demonstrate empirically why observability code must not run inside workflow
code — the architecture suggested by Langfuse's Temporal integration guide.

What it does (mirroring that guide):

- Creates OpenTelemetry spans **inside workflow code** with a **plain**
  tracer provider (random span IDs, unconditional export).
- **Disables the workflow sandbox** so the tracing/LLM libraries are
  importable from workflow code.
- Uses **no Temporal OpenTelemetry integration** — no replay awareness, no
  context propagation into activities.

The worker disables the workflow cache (`max_cached_workflows=0`) so that
replay — which production triggers intermittently via worker restarts,
deploys, and cache evictions — happens on every workflow task and the
breakage is immediately visible.

## Run the experiment

```bash
uv run python -m langfuse_tracing.naive_guide_style.worker
uv run python -m langfuse_tracing.naive_guide_style.starter
uv run python -m langfuse_tracing.verify_trace --count-generations --since-minutes 3
```

## Measured result

One workflow run (two LLM steps) produced **6 disconnected Langfuse traces**
containing **12 copies of 5 logical spans**:

```
trace 1  research-agent, agent-step-1, agent-step-2     (the only complete-looking copy)
trace 2  research-agent, agent-step-1                   (replay duplicate)
trace 3  research-agent, agent-step-1                   (replay duplicate)
trace 4  research-agent, agent-step-1, agent-step-2     (replay duplicate)
trace 5  ChatCompletion [GENERATION]                    (orphaned — no workflow context)
trace 6  ChatCompletion [GENERATION]                    (orphaned — no workflow context)
```

Why: every replay re-executes the workflow function from the top, and a plain
tracer re-creates the same spans with fresh random IDs and re-exports them —
each replay becomes a new partial trace. Meanwhile the LLM spans from the
activities have no propagated parent, so they land in traces of their own.
This is precisely the "wrong event types and broken nesting" symptom, plus
duplicates that grow with every replay.

Compare with [../ticket_triage/](../ticket_triage/): same worker-cache
setting, one trace, every span exactly once — because the
`OpenTelemetryPlugin`'s tracer provider derives span IDs deterministically
from workflow state, suppresses re-export during replay, and propagates
context through Temporal headers persisted in workflow history.
