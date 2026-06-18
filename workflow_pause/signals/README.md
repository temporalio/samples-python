# Workflow Pause: signals are buffered while paused

A signal sent to a **paused** workflow is accepted and recorded in history, but its handler does not
run until the workflow is **unpaused** — then the buffered signals are processed in order.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

```bash
uv run workflow_pause/signals/worker.py
```

Start the workflow in a second terminal:

```bash
uv run workflow_pause/signals/starter.py
```

Pause the workflow:

```bash
temporal workflow pause -w pause-signals-wf --reason demo
```

Now send a signal while paused — it succeeds (it is recorded in history):

```bash
temporal workflow signal -w pause-signals-wf --name add_message --input '"hello"'
```

But the handler has **not** run yet. Confirm by querying once unpaused (queries are rejected while
paused — see the `queries` sample). Unpause:

```bash
temporal workflow unpause -w pause-signals-wf
```

The worker now logs `Received message: hello` — the buffered signal was processed on unpause.
Confirm the buffered message landed by querying the workflow (queries work again now that it is
unpaused):

```bash
temporal workflow query -w pause-signals-wf --type messages
# ["hello"]
```

Send a `"done"` signal to let the workflow complete:

```bash
temporal workflow signal -w pause-signals-wf --name add_message --input '"done"'
```
