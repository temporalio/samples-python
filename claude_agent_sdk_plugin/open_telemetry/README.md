# OpenTelemetry

Trace a Workflow and the Claude Code it runs as one OpenTelemetry trace: the caller, the Workflow, its Activities, and Claude Code's own model and tool spans.

## What this shows

- **One trace across processes.** `OpenTelemetryPlugin` carries the trace from the starter into the Workflow and its Activities. The plugin passes it on to Claude Code in `TRACEPARENT`, so Claude Code's spans join the same trace.
- **Claude Code's own spans.** Each turn is a `claude_code.interaction` span, with a `claude_code.llm_request` span for each model call and a `claude_code.tool` span for each tool call.
- **Replay-safe Workflow spans.** `create_tracer_provider()` gives Workflow spans IDs that stay the same on replay, and exports them once.

## Run it

All commands run from the repository root. Start a Temporal dev server in a separate terminal:

```bash
temporal server start-dev
```

Start [Jaeger](https://www.jaegertracing.io/) to receive and show the traces. It takes OTLP on port 4317:

```bash
docker run --rm -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
```

Start the Worker in another terminal:

```bash
uv run --group claude-agent-sdk claude_agent_sdk_plugin/open_telemetry/run_worker.py
```

The Worker runs offline: everything runs for real except the model, which asks for one Bash command and then answers with fixed text. To use the real model, put `ANTHROPIC_API_KEY=...` in front of the command.

The Worker sets Claude Code's tracing variables in its own environment, from [telemetry.py](telemetry.py):

```bash
CLAUDE_CODE_ENABLE_TELEMETRY=1
CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Run the Workflow from a third terminal:

```bash
uv run --group claude-agent-sdk python -m claude_agent_sdk_plugin.open_telemetry.run_workflow
```

## Expected behavior

The starter prints the result and the trace ID:

```
Result: I counted the Python files with ls.
Trace ID: aa8b95b37c1b39f76cc9102fa3d1d5b9
```

Open the trace at `http://localhost:16686/trace/<trace ID>`. It spans three services:

```
ask-agent                                                 claude-agent-sdk-starter
└─ StartWorkflow:OpenTelemetryWorkflow                    claude-agent-sdk-starter
   └─ RunWorkflow:OpenTelemetryWorkflow                   claude-agent-sdk-worker
      ├─ StartActivity:claude-agent-sdk-connect           claude-agent-sdk-worker
      │  └─ RunActivity:claude-agent-sdk-connect          claude-agent-sdk-worker
      │     └─ claude_code.interaction                    claude-code
      │        ├─ claude_code.llm_request
      │        ├─ claude_code.tool
      │        │  ├─ claude_code.tool.blocked_on_user
      │        │  └─ claude_code.tool.execution
      │        └─ claude_code.llm_request
      ├─ StartActivity:claude-agent-sdk-write             (one per write)
      │  └─ RunActivity:claude-agent-sdk-write
      ├─ StartActivity:claude-agent-sdk-read              (one per read)
      │  └─ RunActivity:claude-agent-sdk-read
      └─ StartActivity:claude-agent-sdk-close
         └─ RunActivity:claude-agent-sdk-close
```
