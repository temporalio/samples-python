# Workflow Pause: in-flight activities & activity-level pause

Demonstrates how pause interacts with activities. The workflow runs a single long-running activity
(`process-item`) that heartbeats for ~5 seconds and is configured to fail its first two attempts
before succeeding, so you can observe both kinds of pause.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

```bash
uv run workflow_pause/activities/worker.py
```

Start the workflow in a second terminal:

```bash
uv run workflow_pause/activities/starter.py
```

## Demo A — pause the workflow while the activity is in flight

While the worker log shows the activity processing (attempt 1), pause the workflow:

```bash
temporal workflow pause -w pause-activities-wf --reason demo
```

The currently running activity attempt is **not** killed — it runs to its conclusion — but because
the workflow is paused, the next workflow task is not dispatched, so the workflow does not advance.
Unpause to let it continue:

```bash
temporal workflow unpause -w pause-activities-wf
```

## Demo B — pause the activity (halt retries)

The activity fails its first two attempts, so it enters a retry backoff. Pause the **activity** so
its retries stop:

```bash
temporal activity pause --activity-id process-item -w pause-activities-wf
```

The activity will not be retried while paused. Resume retries with:

```bash
temporal activity unpause --activity-id process-item -w pause-activities-wf
```

On the third attempt the activity succeeds and the workflow completes with `processed widget`.
