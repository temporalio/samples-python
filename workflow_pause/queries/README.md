# Workflow Pause: queries are rejected while paused

Queries succeed against a running workflow, but are **rejected** while the workflow is paused.
Unpausing makes it queryable again.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

```bash
uv run workflow_pause/queries/worker.py
```

Start the workflow in a second terminal:

```bash
uv run workflow_pause/queries/starter.py
```

Query it while running — this returns the current count:

```bash
temporal workflow query -w pause-queries-wf --type current_count
```

Pause it:

```bash
temporal workflow pause -w pause-queries-wf --reason demo
```

Query again — it is now **rejected**:

```bash
temporal workflow query -w pause-queries-wf --type current_count
# Error: query was rejected, workflow has status: Paused
```

Unpause it and the query works again:

```bash
temporal workflow unpause -w pause-queries-wf
temporal workflow query -w pause-queries-wf --type current_count
```
