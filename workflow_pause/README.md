# Workflow Pause

These samples demonstrate the experimental **Workflow Pause** feature. Pausing a Workflow Execution
tells the Temporal Service to stop dispatching workflow tasks for it — the workflow makes no forward
progress (timers don't advance, signals buffer, queries and updates are rejected) until it is
**unpaused**. See the [Temporal CLI docs](https://docs.temporal.io/cli/workflow#pause).

## Prerequisites

First see the main [README.md](../README.md) for general prerequisites. Then note:

- Requires **Temporal Server 1.31.0+ / CLI 1.7.1+**. The feature is experimental.
- **Pause must be enabled server-side.** Start your dev server with the pause dynamic-config flag:

  ```bash
  temporal server start-dev --dynamic-config-value frontend.WorkflowPauseEnabled=true
  ```

  Without it, `temporal workflow pause` returns
  `Error: workflow pause is not enabled for namespace: default`.

## Samples

* [basic](basic/) — Dead-simple pause / unpause of a workflow waiting on a timer.
* [activities](activities/) — How pause interacts with in-flight activities, plus activity-level
  pause (`temporal activity pause`) to halt retries.
* [signals](signals/) — Signals sent while paused are buffered and processed on unpause.
* [queries](queries/) — Queries are rejected while paused.
* [updates](updates/) — Updates are rejected while paused.
* [cancel_terminate](cancel_terminate/) — Terminate is immediate; cancel is deferred until unpause.
