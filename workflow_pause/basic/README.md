# Workflow Pause: basic pause / unpause

The simplest demonstration of [Workflow Pause](https://docs.temporal.io/cli/workflow#pause).
The workflow loops, sleeping on a timer each iteration. While it is **paused** the timer does
not advance and the iteration count stops; **unpausing** resumes it.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

```bash
uv run workflow_pause/basic/worker.py
```

Start the workflow in a second terminal:

```bash
uv run workflow_pause/basic/starter.py
```

Watch the worker terminal log "Completed iteration N". Now pause it:

```bash
temporal workflow pause -w pause-basic-wf --reason demo
```

The iterations stop — no new "Completed iteration" lines appear. Confirm it is paused:

```bash
temporal workflow describe -w pause-basic-wf
```

The output shows a `Pause Info` section. Now unpause it:

```bash
temporal workflow unpause -w pause-basic-wf
```

The worker resumes logging iterations and the workflow runs to completion.
