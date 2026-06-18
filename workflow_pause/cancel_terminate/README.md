# Workflow Pause: cancel vs terminate on a paused workflow

Shows how cancel and terminate differ when a workflow is paused:

- **Terminate** takes effect immediately, even while paused.
- **Cancel** records a `WorkflowExecutionCancelRequested` event, but the workflow stays `Paused` and
  its cancellation handling does not run until you **unpause** it.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

```bash
uv run workflow_pause/cancel_terminate/worker.py
```

## Terminate a paused workflow (immediate)

Start the workflow in a second terminal:

```bash
uv run workflow_pause/cancel_terminate/starter.py
```

Pause then terminate it — it ends right away:

```bash
temporal workflow pause -w pause-cancel-terminate-wf --reason demo
temporal workflow terminate -w pause-cancel-terminate-wf
temporal workflow describe -w pause-cancel-terminate-wf   # Status: Terminated
```

## Cancel a paused workflow (deferred until unpause)

Start a fresh run (re-running the starter terminates the previous one):

```bash
uv run workflow_pause/cancel_terminate/starter.py
```

Pause it, then request cancellation:

```bash
temporal workflow pause -w pause-cancel-terminate-wf --reason demo
temporal workflow cancel -w pause-cancel-terminate-wf
```

Describe it — the cancel is recorded but the status is still `Paused`:

```bash
temporal workflow describe -w pause-cancel-terminate-wf   # Status: Paused
```

Unpause it — now the workflow processes the cancellation (the worker logs
"Cancellation received — running cleanup") and ends as `Canceled`:

```bash
temporal workflow unpause -w pause-cancel-terminate-wf
temporal workflow describe -w pause-cancel-terminate-wf   # Status: Canceled
```
