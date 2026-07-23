# Recommended: Temporal → Langfuse via OpenTelemetry

**TL;DR** — Use Temporal's built-in OpenTelemetry integration
([`temporalio.contrib.opentelemetry`](https://python.temporal.io/temporalio.contrib.opentelemetry.html))
and export OTLP directly to Langfuse's native OpenTelemetry endpoint. No
Langfuse-specific plugin or SDK is required, workflow code stays deterministic
and sandboxed, and traces come out correctly typed, correctly nested, and
duplicate-free — even across worker restarts and workflow replay. The
runnable sample next to this document demonstrates and verifies all of it.

## Why not the Langfuse Temporal integration guide

Langfuse's [Temporal guide](https://langfuse.com/integrations/frameworks/temporal)
takes an approach that conflicts with Temporal's durable execution model on
three points:

1. **It runs agent/LLM logic inside workflow code and disables the workflow
   sandbox** (`UnsandboxedWorkflowRunner`). The sandbox is what protects
   workflow determinism; turning it off to make I/O-performing libraries
   importable in workflow code trades away durability, replayability, and
   Temporal's retry semantics for the part of your application that needs them
   most. Model calls belong in activities.

2. **It instruments the LLM SDK globally, so spans are created from workflow
   code.** Temporal workflows re-execute ("replay") their code on worker
   restarts, deploys, and cache evictions — that is how durable execution
   works. A plain OpenTelemetry tracer knows nothing about replay: every
   replay re-creates the same spans with fresh random span IDs and re-exports
   them. Langfuse does not deduplicate unrelated span IDs, so duplicates
   accumulate.

3. **It hand-propagates trace context** (`gen_trace_id()` passed through
   workflow arguments) instead of using Temporal's header-based context
   propagation, so spans from activities — which usually run on other
   processes or machines — don't reliably nest under the workflow's trace.

### Measured, not argued

The sample contains a deliberately broken `naive_guide_style/` variant that
mirrors that architecture (spans created in workflow code, sandbox off, no
Temporal OpenTelemetry integration), run against a worker whose workflow cache
is disabled so that replay — which in production happens intermittently —
happens on every workflow task. The result of **one** workflow run with two
LLM steps:

| | Recommended pattern (`ticket_triage/`) | Guide-style (`naive_guide_style/`) |
|---|---|---|
| Langfuse traces per workflow run | **1** | **6**, disconnected |
| Observations | **15**, correctly nested tree | **12 copies of 5 logical spans** (`research-agent` ×4, `agent-step-1` ×4, `agent-step-2` ×2) |
| LLM GENERATIONs | nested under their activity | orphaned in their own traces, no workflow context |
| Worker killed mid-workflow | same single clean tree | more duplicates, more fragments |

Because replay in production is triggered by cache pressure and restarts, the
guide-style breakage is *intermittent*: traces look fine in a quick test and
degrade in production. The Langfuse symptoms reported as "wrong event types
and nesting" are exactly what this failure mode looks like from the UI.

## The recommended architecture

```
starter process                      worker process
┌─────────────────────────┐          ┌──────────────────────────────────────┐
│ root span (langfuse.*)  │          │ OpenTelemetryPlugin                  │
│  └ StartWorkflow ───────┼──────────┼─→ RunWorkflow (workflow, sandboxed)  │
│  └ StartWorkflowUpdate ─┼─headers──┼─→   └ activities (all LLM calls)     │
│                         │          │        └ GENERATION spans (auto-     │
│ OTLP/HTTP ↓             │          │          instrumented OpenAI client) │
└─────────────────────────┘          │ OTLP/HTTP ↓                          │
                                     └──────────────────────────────────────┘
                 ↓                                    ↓
        Langfuse  /api/public/otel  (Basic auth: public/secret key)
```

Three pieces, all standard:

1. **`OpenTelemetryPlugin(add_temporal_spans=True)`** on the Temporal client
   in every process (workers inherit it from the client). It emits spans for
   Temporal operations (`StartWorkflow`, `RunWorkflow`, `RunActivity`,
   `HandleUpdate`, …) and propagates trace context across every
   client/workflow/activity boundary in Temporal headers, which are persisted
   in workflow history — so parenting survives replay, worker restarts, and
   multi-worker execution. Its tracer provider
   (`create_tracer_provider()`) generates span IDs deterministically from
   workflow state and suppresses re-export during replay: each logical span is
   emitted once, and even a crash-forced re-export carries the same IDs, which
   Langfuse upserts rather than duplicates. Workflow code can use plain
   OpenTelemetry APIs (`tracer.start_as_current_span(...)`) and stays fully
   sandboxed — the plugin adds the necessary passthrough itself.

2. **An OTel auto-instrumentation for your LLM SDK, applied in the worker.**
   LLM calls live in activities, so instrumentation spans are created in
   ordinary (non-replaying) code — no replay concerns at all. Any
   instrumentation that emits GenAI/OpenInference-style attributes works;
   Langfuse derives the observation type GENERATION plus model, token usage,
   and cost from them.

3. **A standard OTLP/HTTP exporter pointed at Langfuse** — Langfuse ingests
   native OpenTelemetry:

   ```python
   OTLPSpanExporter(
       endpoint=f"{LANGFUSE_HOST}/api/public/otel/v1/traces",  # HTTP only; no gRPC
       headers={
           "Authorization": f"Basic {base64(public_key + ':' + secret_key)}",
           "x-langfuse-ingestion-version": "4",  # real-time ingestion
       },
   )
   ```

## What you see in Langfuse

One trace per workflow run, with observation types derived automatically —
Temporal operations as SPANs with real durations, LLM calls as GENERATIONs
with model/usage/cost, and update handlers visible as first-class events:

```
ticket-triage                                   SPAN   (trace root; session/user/tags set here)
├─ StartWorkflow:TicketTriageWorkflow           SPAN   (client)
│  └─ RunWorkflow:TicketTriageWorkflow          SPAN   (workflow, real duration)
│     ├─ triage                                 SPAN   (custom span in workflow code)
│     │  ├─ StartActivity:classify_ticket → RunActivity:classify_ticket
│     │  │  └─ ChatCompletion                   GENERATION  (model, tokens, cost, input/output)
│     │  └─ StartActivity:lookup_account  → RunActivity:lookup_account
│     └─ StartActivity:draft_reply → RunActivity:draft_reply
│        └─ ChatCompletion                      GENERATION
└─ StartWorkflowUpdate:approve                  SPAN   (client)
   ├─ ValidateUpdate:approve                    SPAN
   └─ HandleUpdate:approve                      SPAN
```

The sample's `verify_trace.py` asserts this tree — including types, token
usage, and the absence of duplicates — through the Langfuse public API, and
passes after: a normal run, a run with the workflow cache disabled (replay on
every workflow task), and a run where the worker was killed mid-workflow and
replaced. The trace was identical in all three.

### Trace-level enrichment

Langfuse trace fields are set with span attributes on the trace's root span
(the starter is the natural place):

```python
with tracer.start_as_current_span("ticket-triage", attributes={
    "langfuse.trace.name": "ticket-triage",
    "langfuse.session.id": workflow_id,   # group runs; find traces by workflow ID
    "langfuse.user.id": user_id,
    "langfuse.trace.tags": ["temporal"],
    "langfuse.trace.metadata.temporal_workflow_id": workflow_id,
}):
    handle = await client.start_workflow(...)
```

Temporal's spans also carry `temporalWorkflowID`/`temporalRunID` attributes,
so any observation can be tied back to the exact workflow execution in the
Temporal UI.

## Operational notes

- **Langfuse's OTLP endpoint is HTTP-only** (protobuf or JSON). Use
  `opentelemetry-exporter-otlp-proto-http`, not the gRPC exporter.
- **Flush before short-lived processes exit.** `BatchSpanProcessor` buffers;
  call `provider.force_flush()` at the end of starters and on worker shutdown
  or the last spans are silently dropped.
- **Use a fresh workflow ID per run.** It becomes the natural Langfuse
  session ID, and it avoids ever-growing traces from ID reuse.
- **Long-running workflows:** activity and LLM observations stream into the
  trace as they complete; the enclosing `RunWorkflow` span is exported when
  the run finishes.
- **Kill switch:** `OTEL_SDK_DISABLED=true` disables export without code
  changes.
- **Self-hosting:** Langfuse is MIT-licensed; the sample ships a pinned
  `docker-compose.yml` with headless provisioning (org, project, API keys)
  for a zero-click local setup.

## Other SDKs

The same architecture applies beyond Python: Temporal's TypeScript SDK ships
OpenTelemetry interceptors (`@temporalio/interceptors-opentelemetry`), and
equivalent OpenTelemetry interceptors exist for the Go, Java, and .NET SDKs.
Any of them can feed Langfuse's OTLP endpoint the same way.

---

*See `README.md` in this directory for the runnable sample and the
verification runbook.*
