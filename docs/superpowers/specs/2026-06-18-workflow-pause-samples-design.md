Status: in-progress

# Workflow Pause Samples — Design

## Purpose

Showcase the **Workflow Pause** feature for internal Temporal users (sales/customer-facing).
When a workflow execution is paused, the service stops dispatching workflow tasks for it —
no new workflow tasks run, so the workflow makes no forward progress — until it is unpaused.
The feature is experimental (Temporal Server 1.31.0, CLI 1.7.1+) and exposed via:

- `temporal workflow pause -w <id>` / `temporal workflow unpause -w <id>` — workflow-level
- `temporal activity pause` / `temporal activity unpause` — activity-level (halts an activity's
  retries; kicks in at the next time the activity fails/completes/times out)

These samples give internal users hands-on, copy-pasteable demonstrations of what pause does and
how it interacts with timers, activities, signals, queries, updates, cancel, and terminate.

## Audience & Constraints

- **Interaction is via the `temporal` CLI only.** Each sample ships a worker and a starter; all
  pause/unpause/signal/query/update/cancel/terminate interaction is done with `temporal ...`
  commands documented in the sample's README. No Python interactor scripts.
- **Fixed Workflow IDs** in each starter (e.g. `pause-basic-wf`) so README CLI commands are
  copy-pasteable without substitution.
- Follow existing repo conventions (mirrors `message_passing/*`): per-sample directory with
  `__init__.py` (holds `TASK_QUEUE`), `worker.py` (long-running, waits on interrupt),
  `workflow.py`, `activities.py` (where needed), `starter.py`, `README.md`.
- Loads client config via `ClientConfig.load_client_connect_config()` with
  `target_host` defaulting to `localhost:7233`, matching other samples.

## Sample Catalog (6 samples)

All live under `workflow_pause/`. Each is fully self-contained and independently runnable.

| # | Directory | Demonstrates |
|---|-----------|--------------|
| 1 | `basic` | Dead-simple pause/unpause. Workflow waits on a timer; pause freezes it, unpause resumes. Covers basic pause + timers/timeouts. |
| 2 | `activities` | In-flight activity continues across a *workflow* pause; `temporal activity pause` independently halts an activity's retries. Covers in-flight activities + activity-level pause interaction. |
| 3 | `signals` | Signals sent while paused are recorded but buffered; handler runs only after unpause. |
| 4 | `queries` | Queries are **rejected** while the workflow is paused (`query was rejected, workflow has status: Paused`); unpause restores them. |
| 5 | `updates` | Update requests are **rejected** while paused (`Workflow is paused. Cannot update the workflow.`); unpause restores them. |
| 6 | `cancel_terminate` | Terminate takes effect immediately on a paused workflow; cancel is delivered only after unpause. |

### Common workflow shape

Most samples use a **progress-loop workflow** so "no progress while paused" is visible in worker
logs and in `temporal workflow describe`:

```python
@workflow.defn
class PauseDemoWorkflow:
    def __init__(self) -> None:
        self._count = 0

    @workflow.run
    async def run(self, iterations: int) -> int:
        for i in range(iterations):
            # activity / log marking forward progress
            await workflow.execute_activity(...)   # samples that need an activity
            self._count += 1
            await workflow.sleep(timedelta(seconds=...))  # the timer that pause freezes
        return self._count
```

Samples 3–5 add the relevant `@workflow.signal` / `@workflow.query` / `@workflow.update` handler
on top of this base. Sample 1 is the loop with only a timer (no activity). Sample 6 reuses the
loop and is driven entirely by external cancel/terminate.

## Per-sample detail

### 1. `basic`
- **Workflow**: loops N times, logging progress and sleeping on a timer each iteration. No activity.
- **Demo**: start → observe iterations advancing in worker log → `temporal workflow pause` →
  iterations stop, `temporal workflow describe` shows paused → `temporal workflow unpause` →
  iterations resume → completes.

### 2. `activities`
- **Activity**: a long-running activity (heartbeats, sleeps several seconds, configured to fail and
  retry a couple of times to make retry-pausing observable). `activity-id` set explicitly so the
  CLI can target it.
- **Workflow**: runs the activity, then continues.
- **Demo A (workflow pause vs in-flight activity)**: start → while activity is in flight,
  `temporal workflow pause` → the already-running activity completes (it isn't killed), but the
  *next* workflow task isn't dispatched, so the workflow doesn't advance past it until unpause.
- **Demo B (activity pause)**: `temporal activity pause --activity-id <id> -w <id>` → activity
  retries stop after the current attempt ends → `temporal activity unpause ...` → retries resume.

### 3. `signals`
- **Workflow**: progress loop with a `@workflow.signal` that appends to an internal list / bumps a
  counter; a query exposes the received signals so the effect is observable.
- **Demo**: pause → `temporal workflow signal -w <id> --name <sig> --input ...` (accepted, recorded
  in history) → query/describe shows handler has NOT run → unpause → buffered signal(s) processed.

### 4. `queries`
- **Workflow**: progress loop with a `@workflow.query` returning current state.
- **Demo**: query before pause returns state → `temporal workflow pause` → `temporal workflow query
  -w <id> --type <q>` is **rejected** with `Error: query was rejected, workflow has status: Paused`
  → `temporal workflow unpause` → query returns state again.

### 5. `updates`
- **Workflow**: progress loop with a `@workflow.update` (e.g. set/adjust a value, returns new value).
- **Demo**: pause → `temporal workflow update execute -w <id> --name <u> --input ...` is **rejected
  immediately** with `Error: unable to update workflow: Workflow is paused. Cannot update the
  workflow.` → unpause → update admitted and result returned.

### 6. `cancel_terminate`
- **Workflow**: progress loop that handles cancellation (try/except `asyncio.CancelledError` to log
  cleanup) so the cancel-vs-terminate difference is observable.
- **Demo terminate**: pause → `temporal workflow terminate -w <id>` → ends immediately (works while
  paused).
- **Demo cancel**: (fresh run) pause → `temporal workflow cancel -w <id>` → a
  `WorkflowExecutionCancelRequested` event is recorded but `describe` still shows status
  `WORKFLOW_EXECUTION_STATUS_PAUSED`; the workflow's cancellation handling runs only after
  `temporal workflow unpause`, after which status becomes `CANCELED`.

## Verified pause behavior (empirically confirmed against Server 1.31.0)

Confirmed via a throwaway probe against a local dev server started with the pause dynamic-config
flag enabled. These are the behaviors the samples and READMEs are written to match:

| Operation while paused | Behavior |
|---|---|
| Query | **Rejected**: `query was rejected, workflow has status: Paused` |
| Update | **Rejected immediately**: `Workflow is paused. Cannot update the workflow.` |
| Signal | Accepted & recorded in history; handler **buffered**, runs on unpause |
| Cancel | `WorkflowExecutionCancelRequested` recorded; status stays `PAUSED`; acted on after unpause → `CANCELED` |
| Terminate | Takes effect immediately |
| Timer / loop iterations | Frozen; resume on unpause |

Additional confirmed details used by the samples/READMEs:
- **Pause must be enabled server-side** via a dynamic-config flag; without it the CLI returns
  `Error: workflow pause is not enabled for namespace: default`. READMEs must document starting the
  dev server with the pause flag enabled:
  `temporal server start-dev --dynamic-config-value frontend.WorkflowPauseEnabled=true`
- `temporal workflow describe` on a paused workflow shows a `Pause Info` section and a
  `TemporalPauseInfo` search attribute (`["Workflow:<id>","Reason:<reason>"]`).
- Paused status enum is `WORKFLOW_EXECUTION_STATUS_PAUSED` (visible via `describe -o json`).

## Top-level `workflow_pause/README.md`

An index README at `workflow_pause/README.md` that:
- Explains the Workflow Pause feature in one short paragraph + link to docs.
- Notes prerequisites (Server 1.31.0 / CLI 1.7.1+, experimental) once, centrally.
- Lists all six samples with a one-line description and a link to each sample dir,
  mirroring how the root README's `## Samples` section is structured.

## README format (each sample)

Mirrors existing samples, then adds the pause-specific CLI walkthrough:

1. One-line description + link to pause docs.
2. Prereqs: link to root README; note Server 1.31.0 / CLI 1.7.1+, that pause is experimental, and
   that the dev server must be started with
   `--dynamic-config-value frontend.WorkflowPauseEnabled=true` (link to the top-level
   `workflow_pause/README.md` which documents this centrally).
3. Terminal 1: `uv run workflow_pause/<sample>/worker.py`
4. Terminal 2: `uv run workflow_pause/<sample>/starter.py`
5. Terminal 2 (interaction): the relevant `temporal workflow pause/unpause/...` commands with the
   fixed Workflow ID, and the expected observable outcome at each step.

## Repo integration

- Add `workflow_pause/README.md` (index, see above).
- Add the six samples to the `## Samples` list in the root `README.md` (alphabetical position:
  after `worker_versioning`, before `Test`, under a `workflow_pause/*` grouping consistent with how
  `message_passing/*` is listed).
- No new third-party dependencies — uses only `temporalio` (already a core dependency).

## Testing

- Follow repo test conventions (`tests/` mirrors sample layout where applicable). Given these are
  CLI-driven demos, automated tests will at minimum cover that each workflow runs to completion
  against the time-skipping/dev test environment without pause (sanity), since pause itself is a
  server-side CLI operation not exercised by the SDK test harness. Manual CLI verification is the
  primary validation and is documented per-sample README.

## Out of scope

- Programmatic pause via SDK client (feature is CLI/server-side; no Python pause API used here).
- Batch pause (`temporal batch`) of multiple workflows.
- UI-based pause walkthroughs.
