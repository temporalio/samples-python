# Langfuse Tracing

This sample shows the recommended way to get Temporal workflow traces into
[Langfuse](https://langfuse.com/): Temporal's
[`OpenTelemetryPlugin`](https://python.temporal.io/temporalio.contrib.opentelemetry.html)
plus a standard OTLP/HTTP exporter pointed at Langfuse's native OpenTelemetry
endpoint. No Langfuse SDK or Langfuse-specific plugin is involved, workflow
code stays deterministic and sandboxed, and traces are correctly nested,
correctly typed, and duplicate-free across replay and worker restarts.

Contents:

- **[ticket_triage/](ticket_triage/)** — the recommended pattern: an LLM
  ticket-triage workflow (two LLM activities, one plain activity, one human
  approval delivered as a workflow update).
- **[verify_trace.py](verify_trace.py)** — checks a trace via the Langfuse
  public API: whole-tree equality, observation types, token usage, and
  no-duplicates.
- **[langfuse/docker-compose.yml](langfuse/docker-compose.yml)** — pinned
  self-hosted Langfuse with org/project/API keys provisioned headlessly.
- **[telemetry.py](telemetry.py)** — the OpenTelemetry wiring (replay-safe
  tracer provider, OTLP exporter with Langfuse auth, LLM instrumentation).

## Prerequisites

- Docker (for Langfuse), a local Temporal server
  (`temporal server start-dev`), and `uv`.
- An OpenAI-compatible LLM endpoint: either a real `OPENAI_API_KEY`, or any
  OpenAI-compatible gateway via `OPENAI_BASE_URL`.

## Run it

```bash
# 1. Start Langfuse (first pull takes a few minutes)
cd langfuse_tracing/langfuse
docker compose up -d
curl -sf http://localhost:3000/api/public/health   # repeat until {"status":"OK",...}
# UI: http://localhost:3000 — login demo@temporal.io / langfuse-demo-pw-1

# 2. Install dependencies and set environment (repo root)
cd ../..
uv sync --group langfuse-tracing
cp langfuse_tracing/.env.example langfuse_tracing/.env   # edit the LLM settings
set -a; source langfuse_tracing/.env; set +a

# 3. Run the sample (two terminals, same environment)
uv run python -m langfuse_tracing.ticket_triage.worker
uv run python -m langfuse_tracing.ticket_triage.starter

# 4. Verify the trace through the Langfuse API (uses the printed trace ID)
uv run python -m langfuse_tracing.verify_trace --trace-id <printed trace id>
```

The starter prints a direct link to the trace in the Langfuse UI. You should
see one trace shaped like this (types as Langfuse derives them):

```
ticket-triage                                   SPAN   (root; session/user/tags)
├─ StartWorkflow:TicketTriageWorkflow           SPAN
│  └─ RunWorkflow:TicketTriageWorkflow          SPAN
│     ├─ triage                                 SPAN   (custom span from workflow code)
│     │  ├─ StartActivity:classify_ticket → RunActivity:classify_ticket
│     │  │  └─ ChatCompletion                   GENERATION  (model, tokens, cost)
│     │  └─ StartActivity:lookup_account  → RunActivity:lookup_account
│     └─ StartActivity:draft_reply → RunActivity:draft_reply
│        └─ ChatCompletion                      GENERATION
└─ StartWorkflowUpdate:approve                  SPAN
   ├─ ValidateUpdate:approve                    SPAN
   └─ HandleUpdate:approve                      SPAN
```

## Prove the replay-safety claims

Durable execution means workflow code re-executes (replays) on worker
restarts and cache evictions. These two experiments show tracing is
unaffected — each run still verifies cleanly with the same tree shape and no
duplicate observations:

```bash
# Replay stress: disable the workflow cache so EVERY workflow task replays
# the workflow from the start of history.
uv run python -m langfuse_tracing.ticket_triage.worker --replay-stress
uv run python -m langfuse_tracing.ticket_triage.starter
uv run python -m langfuse_tracing.verify_trace --trace-id <printed trace id>

# Worker restart mid-workflow: the starter waits 20s before sending the
# approval. Give the triage activities a few seconds to finish, then kill the
# worker while the workflow durably awaits approval; start a new worker and
# watch the workflow (and its trace) complete cleanly.
uv run python -m langfuse_tracing.ticket_triage.starter --pause-before-approval 20
#   ... after ~5s, ctrl+c the worker, then start it again in another terminal
uv run python -m langfuse_tracing.verify_trace --trace-id <printed trace id>
```

## Where spans come from

| Span | Emitted by | Where it runs |
|---|---|---|
| `ticket-triage` (root) + `langfuse.*` trace attributes | starter code | starter |
| `StartWorkflow:*`, `StartWorkflowUpdate:*` | `OpenTelemetryPlugin` | starter (client side) |
| `RunWorkflow:*`, `StartActivity:*`, `ValidateUpdate:*`, `HandleUpdate:*` | `OpenTelemetryPlugin` | worker (workflow) |
| `triage` | plain OpenTelemetry API in workflow code | worker (workflow) |
| `RunActivity:*` | `OpenTelemetryPlugin` | worker (activity) |
| `ChatCompletion` / `chat <model>` GENERATIONs | OpenAI auto-instrumentation | worker (activity) |

## Where tracing works

| Location | Works? | Notes |
|---|---|---|
| Activity bodies | ✅ | Plain OpenTelemetry + any auto-instrumentation, no restrictions. This is where LLM calls (and their GENERATION spans) belong. |
| Workflow bodies | ✅ | Plain OpenTelemetry APIs are replay-safe under the plugin: deterministic span IDs, no re-export on replay. Spans export when they end; the `RunWorkflow` span exports when the run completes. |
| Signal/query/update handlers | ✅ | Handled by the plugin automatically (`HandleUpdate:*` etc.). |
| Client / starter code | ✅ | Standard OpenTelemetry; put Langfuse trace-level attributes on your root span. |

## LLM instrumentation flavors

`LLM_INSTRUMENTATION` selects how OpenAI calls are instrumented (both are
verified against Langfuse by this sample):

| | `openinference` (default) | `openai-v2` |
|---|---|---|
| Package | `openinference-instrumentation-openai` | `opentelemetry-instrumentation-openai-v2` |
| Semantic conventions | OpenInference | OpenTelemetry GenAI (`gen_ai.*`) |
| GENERATION type, model, token usage, cost | ✅ | ✅ |
| Prompt/completion content | ✅ by default | Requires `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` and `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_only` |
| GENERATION span name | `ChatCompletion` | `chat <model>` |

## Operational notes

- Langfuse's OTLP endpoint is HTTP-only — this sample uses
  `opentelemetry-exporter-otlp-proto-http` (the gRPC exporter will not work).
- Short-lived processes must flush: the starter and worker call
  `force_flush()` on exit (see `telemetry.py`).
- Use a fresh workflow ID per run: the starter reports it as the Langfuse
  session ID, so each run groups cleanly in the Sessions view. (The trace
  itself is keyed by the starter's root span, which is new on every run.)
- `OTEL_SDK_DISABLED=true` turns off export without code changes.
- Ingestion is asynchronous; `verify_trace.py` polls until the trace is
  stable.

## Tests

`tests/langfuse_tracing/` runs without Langfuse, Docker, or an LLM: mocked
activities, an in-memory span exporter, a worker with the workflow cache
disabled, whole-tree span assertions, and a `Replayer` pass asserting that
replaying the finished workflow's history emits zero new spans.

```bash
uv run --group langfuse-tracing pytest tests/langfuse_tracing -v
```

## Using this outside samples-python

The sample is self-contained: copy the `langfuse_tracing/` directory, change
the absolute imports (`langfuse_tracing.ticket_triage.activities` →
`ticket_triage.activities` or similar), and install the dependencies listed
under `langfuse-tracing` in this repo's `pyproject.toml`.
