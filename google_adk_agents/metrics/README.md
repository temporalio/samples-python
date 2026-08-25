# Google ADK replay-safe metrics

This sample exports Google ADK's OpenTelemetry metrics to a local Prometheus endpoint while preventing Workflow replay from recording the same observations again. The default scripted model is deterministic and makes no network model calls, so no API key is needed.

Start a local Temporal development server:

```shell
temporal server start-dev
```

In another terminal, start the worker from the repository root:

```shell
uv run --project google_adk_agents/metrics python -m google_adk_agents.metrics.run_worker
```

Then run the Workflow:

```shell
uv run --project google_adk_agents/metrics python -m google_adk_agents.metrics.run_metrics_workflow
```

The starter prints `Replay-safe metrics are ready.` Inspect the metrics exposed by the worker:

```shell
curl http://127.0.0.1:9464/metrics | rg 'gen_ai'
```

The output includes `gen_ai.invoke_agent` metrics, `gen_ai.client.operation.duration`, and `gen_ai.client.token.usage` from instrumentation scope `gcp.vertex.agent`. The worker sets `max_cached_workflows=0`, forcing replay between Workflow tasks. `ReplaySafeMeterProvider` drops observations made while replaying, so replay does not multiply the recorded counts.

OpenTelemetry's global meter provider can be installed only once per process. `run_worker.py` installs the replay-safe provider before importing Google ADK or the Workflow. Applications embedding this setup must likewise make it the first and only global meter provider installation in that process.
