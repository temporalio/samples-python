# Workflow Pause: updates are rejected while paused

An update issued against a **paused** workflow is rejected immediately. Unpausing lets updates be
admitted and executed again.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

```bash
uv run workflow_pause/updates/worker.py
```

Start the workflow in a second terminal:

```bash
uv run workflow_pause/updates/starter.py
```

Send an update while running — it returns the new total:

```bash
temporal workflow update execute -w pause-updates-wf --name add --input 5
```

Pause it:

```bash
temporal workflow pause -w pause-updates-wf --reason demo
```

Send an update while paused — it is **rejected** immediately:

```bash
temporal workflow update execute -w pause-updates-wf --name add --input 5
# Error: unable to update workflow: Workflow is paused. Cannot update the workflow.
```

Unpause it and updates work again. Finish the workflow with the `finish` update:

```bash
temporal workflow unpause -w pause-updates-wf
temporal workflow update execute -w pause-updates-wf --name add --input 3
temporal workflow update execute -w pause-updates-wf --name finish
```
