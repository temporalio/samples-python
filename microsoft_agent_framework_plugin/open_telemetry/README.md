# OpenTelemetry

One trace for a Workflow and the agent it runs: the starter's root span, the Workflow, Agent Framework's own `invoke_agent` span, the model Activity, and the OpenAI client's `chat` span inside that Activity.

## What this sample demonstrates

- `Client.connect(plugins=[OpenTelemetryPlugin(add_temporal_spans=True), MicrosoftAgentFrameworkPlugin(...)])` on the Worker's Client: tracing first, so the Worker inherits both in that order. The starter's Client carries `OpenTelemetryPlugin` alone and propagates the trace into the Workflow.
- `create_tracer_provider()` from `temporalio.contrib.opentelemetry` as the global provider in both processes, from [telemetry.py](telemetry.py). Agent Framework starts its `invoke_agent` span from Workflow code, so the provider has to be replay-safe: Workflow spans keep their ids across replays and are exported once. With a plain SDK `TracerProvider` the plugin warns at Worker start, and `OpenTelemetryPlugin` refuses to start the Worker.
- The OpenAI client's own `chat gpt-4o-mini` span runs inside the Activity with real timings.

## Running the sample

Start a Temporal dev server in one terminal:

```bash
temporal server start-dev
```

Start [Jaeger](https://www.jaegertracing.io/) to receive and show the traces. It takes OTLP on port 4317, the default in `telemetry.py`; set `OTEL_EXPORTER_OTLP_ENDPOINT` to send the spans somewhere else:

```bash
docker run --rm -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
```

Without a collector the Workflow still completes; each process logs an export warning and an export error, and the starter exits a few seconds late.

Then the Worker and the starter, from the repository root:

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/open_telemetry/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/open_telemetry/run_workflow.py
```

The starter prints the result and the trace id:

```
Result: Durable execution runs code to completion despite failures, by recording progress and resuming from it.
Trace ID: aa8b95b37c1b39f76cc9102fa3d1d5b9
```

Open `http://localhost:16686/trace/<trace ID>`. The trace spans two services:

```
ask-agent                                                          microsoft-agent-framework-starter
└─ StartWorkflow:TracedWorkflow                                    microsoft-agent-framework-starter
   └─ RunWorkflow:TracedWorkflow                                   microsoft-agent-framework-worker
      └─ invoke_agent assistant                                    microsoft-agent-framework-worker
         └─ StartActivity:microsoft_agent_framework.invoke_model   microsoft-agent-framework-worker
            └─ RunActivity:microsoft_agent_framework.invoke_model  microsoft-agent-framework-worker
               └─ chat gpt-4o-mini                                 microsoft-agent-framework-worker
```

## Files

| File | Description |
|------|-------------|
| `telemetry.py` | `install_tracer_provider`: a replay-safe provider with an OTLP gRPC exporter |
| `workflow.py` | `TracedWorkflow` with one named `Agent` |
| `run_worker.py` | Both plugins on the Client, starts the Worker |
| `run_workflow.py` | Starts the Workflow under a root span and prints the trace id |
