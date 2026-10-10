# Google ADK replay-safe metrics

This sample exports Google ADK's OpenTelemetry metrics to a local Prometheus endpoint while preventing Workflow replay from recording the same observations again. The default scripted model is deterministic and makes no network model calls, so no API key is needed.

Start a local Temporal development server:

```shell
temporal server start-dev
```

In another terminal, start the worker from the repository root:

```shell
uv run python -m google_adk_agents.metrics.run_worker
```

Then run the Workflow:

```shell
uv run python -m google_adk_agents.metrics.run_metrics_workflow
```

The starter prints `Replay-safe metrics are ready.` Inspect the metrics exposed by the worker:

```shell
curl -s http://127.0.0.1:9464/metrics | grep gen_ai
```

The output includes `gen_ai.invoke_agent`, `gen_ai.client.operation.duration`, and `gen_ai.client.token.usage` metrics. Prometheus replaces dots with underscores, so an exported line looks like `gen_ai_invoke_agent_duration_seconds_count{gen_ai_agent_name="metrics_agent"} 1.0`. `ReplaySafeMeterProvider` drops observations made while replaying, so replay does not multiply the recorded counts.

Recordings are first-execution-only rather than exactly-once. Replay is suppressed, but a Workflow Task retry re-executes live and can record again, so treat these metrics as at-least-once usage signals.

OpenTelemetry's global meter provider can be installed only once per process. `run_worker.py` installs the replay-safe provider before importing Google ADK or the Workflow. Applications embedding this setup must likewise make it the first and only global meter provider installation in that process.
