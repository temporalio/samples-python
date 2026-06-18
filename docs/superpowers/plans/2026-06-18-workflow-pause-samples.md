# Workflow Pause Samples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build six self-contained `workflow_pause/` samples that demonstrate the experimental Workflow Pause feature, driven entirely by the `temporal` CLI and documented per-sample.

**Architecture:** Each sample is an independent directory under `workflow_pause/` following the existing `message_passing/*` convention: `__init__.py` (holds `TASK_QUEUE` and `WORKFLOW_ID`), `worker.py` (long-running worker), `workflow.py`, `activities.py` (only sample 2), `starter.py`, `README.md`. Interaction (pause/unpause/signal/query/update/cancel/terminate) is performed via `temporal ...` CLI commands documented in each README. Automated tests validate normal (non-paused) workflow/handler behavior using the repo's `client`/`env` fixtures; pause itself is validated manually via the README CLI walkthroughs (behavior empirically confirmed during design).

**Tech Stack:** Python 3.10+, `temporalio>=1.28.0` (already a core dependency — no new deps), `pytest`/`pytest-asyncio`, Temporal Server 1.31.0 / CLI 1.7.1+.

## Global Constraints

- No new third-party dependencies — only `temporalio` (already core).
- Each starter uses a **fixed Workflow ID** (e.g. `pause-basic-wf`) and `WorkflowIDReusePolicy.TERMINATE_IF_RUNNING` so re-running the starter always works for repeated demos.
- Client connection mirrors other samples: `config = ClientConfig.load_client_connect_config(); config.setdefault("target_host", "localhost:7233"); client = await Client.connect(**config)`.
- Workers mirror `message_passing/introduction/worker.py`: long-running, `interrupt_event` shutdown, `logging.basicConfig(level=logging.INFO)`.
- Timers use `await workflow.sleep(timedelta(...))` (repo idiom).
- Pause requires the dev server started with `--dynamic-config-value frontend.WorkflowPauseEnabled=true`. Without it the CLI returns `Error: workflow pause is not enabled for namespace: default`. Every README documents this.
- **Commits are deferred** — the user batches all git commits at the end. Each task's final step is a verification (run the test), NOT a commit.
- Run `uv run poe format` / `uv run poe lint` conventions where applicable; final task runs the formatter/linter.

## Verified pause behavior (drives README copy)

| Operation while paused | Behavior |
|---|---|
| Query | Rejected: `query was rejected, workflow has status: Paused` |
| Update | Rejected immediately: `Workflow is paused. Cannot update the workflow.` |
| Signal | Accepted & recorded; handler buffered, runs on unpause |
| Cancel | `WorkflowExecutionCancelRequested` recorded; status stays `PAUSED`; acted on after unpause → `CANCELED` |
| Terminate | Takes effect immediately |
| Timer / loop | Frozen; resumes on unpause |

## File Structure

```
workflow_pause/
  __init__.py                 # empty package marker
  README.md                   # index of all six samples + central prereqs (Task 7)
  basic/        __init__.py worker.py workflow.py starter.py README.md          # Task 1
  activities/   __init__.py worker.py workflow.py activities.py starter.py README.md  # Task 2
  signals/      __init__.py worker.py workflow.py starter.py README.md          # Task 3
  queries/      __init__.py worker.py workflow.py starter.py README.md          # Task 4
  updates/      __init__.py worker.py workflow.py starter.py README.md          # Task 5
  cancel_terminate/ __init__.py worker.py workflow.py starter.py README.md      # Task 6
tests/
  workflow_pause/__init__.py
  workflow_pause/basic_test.py            # Task 1
  workflow_pause/activities_test.py       # Task 2
  workflow_pause/signals_test.py          # Task 3
  workflow_pause/queries_test.py          # Task 4
  workflow_pause/updates_test.py          # Task 5
  workflow_pause/cancel_terminate_test.py # Task 6
README.md                     # root: add workflow_pause entries (Task 7)
```

Create the package markers once, up front:

- [ ] **Pre-step: create empty package markers**

```bash
touch workflow_pause/__init__.py tests/workflow_pause/__init__.py
```

---

### Task 1: `basic` — dead-simple pause/unpause on a timer

**Files:**
- Create: `workflow_pause/basic/__init__.py`
- Create: `workflow_pause/basic/workflow.py`
- Create: `workflow_pause/basic/worker.py`
- Create: `workflow_pause/basic/starter.py`
- Create: `workflow_pause/basic/README.md`
- Test: `tests/workflow_pause/basic_test.py`

**Interfaces:**
- Produces: `TASK_QUEUE = "workflow-pause-basic-task-queue"`, `WORKFLOW_ID = "pause-basic-wf"`, `BasicPauseWorkflow.run(self, iterations: int) -> int` (returns the number of completed iterations), `BasicPauseWorkflow.completed` query returning `int`.

- [ ] **Step 1: Write the failing test**

Create `tests/workflow_pause/basic_test.py`:

```python
import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.basic import TASK_QUEUE
from workflow_pause.basic.workflow import BasicPauseWorkflow


async def test_basic_workflow_completes(client: Client, env: WorkflowEnvironment):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[BasicPauseWorkflow]):
        result = await client.execute_workflow(
            BasicPauseWorkflow.run,
            3,
            id=f"basic-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert result == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow_pause/basic_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workflow_pause.basic'`.

- [ ] **Step 3: Create `workflow_pause/basic/__init__.py`**

```python
TASK_QUEUE = "workflow-pause-basic-task-queue"
WORKFLOW_ID = "pause-basic-wf"
```

- [ ] **Step 4: Create `workflow_pause/basic/workflow.py`**

```python
from datetime import timedelta

from temporalio import workflow


@workflow.defn
class BasicPauseWorkflow:
    """A loop that logs progress and sleeps on a timer each iteration.

    While the workflow is paused, no workflow tasks are dispatched, so the
    timer does not advance and the iteration count stops moving. Unpausing
    lets it resume from where it left off.
    """

    def __init__(self) -> None:
        self._completed = 0

    @workflow.run
    async def run(self, iterations: int) -> int:
        for i in range(iterations):
            workflow.logger.info("Starting iteration %d of %d", i + 1, iterations)
            await workflow.sleep(timedelta(seconds=3))
            self._completed += 1
            workflow.logger.info("Completed iteration %d of %d", i + 1, iterations)
        return self._completed

    @workflow.query
    def completed(self) -> int:
        return self._completed
```

- [ ] **Step 5: Create `workflow_pause/basic/worker.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from workflow_pause.basic import TASK_QUEUE
from workflow_pause.basic.workflow import BasicPauseWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(client, task_queue=TASK_QUEUE, workflows=[BasicPauseWorkflow]):
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
```

- [ ] **Step 6: Create `workflow_pause/basic/starter.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.basic import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.basic.workflow import BasicPauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        BasicPauseWorkflow.run,
        20,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(f"Pause it with:    temporal workflow pause -w {WORKFLOW_ID} --reason demo")
    print(f"Unpause it with:  temporal workflow unpause -w {WORKFLOW_ID}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Create `workflow_pause/basic/README.md`**

````markdown
# Workflow Pause: basic pause / unpause

The simplest demonstration of [Workflow Pause](https://docs.temporal.io/cli/workflow#pause).
The workflow loops, sleeping on a timer each iteration. While it is **paused** the timer does
not advance and the iteration count stops; **unpausing** resumes it.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

    uv run workflow_pause/basic/worker.py

Start the workflow in a second terminal:

    uv run workflow_pause/basic/starter.py

Watch the worker terminal log "Completed iteration N". Now pause it:

    temporal workflow pause -w pause-basic-wf --reason demo

The iterations stop — no new "Completed iteration" lines appear. Confirm it is paused:

    temporal workflow describe -w pause-basic-wf

The output shows a `Pause Info` section. Now unpause it:

    temporal workflow unpause -w pause-basic-wf

The worker resumes logging iterations and the workflow runs to completion.
````

- [ ] **Step 8: Run the test to verify it passes**

Run: `uv run pytest tests/workflow_pause/basic_test.py -v`
Expected: PASS (1 passed).

- [ ] **Step 9: Verify (no commit — user batches commits at end)**

Run: `uv run pytest tests/workflow_pause/basic_test.py -v` and confirm green. Leave changes staged/unstaged for the user.

---

### Task 2: `activities` — in-flight activity + activity-level pause

**Files:**
- Create: `workflow_pause/activities/__init__.py`
- Create: `workflow_pause/activities/activities.py`
- Create: `workflow_pause/activities/workflow.py`
- Create: `workflow_pause/activities/worker.py`
- Create: `workflow_pause/activities/starter.py`
- Create: `workflow_pause/activities/README.md`
- Test: `tests/workflow_pause/activities_test.py`

**Interfaces:**
- Produces: `TASK_QUEUE = "workflow-pause-activities-task-queue"`, `WORKFLOW_ID = "pause-activities-wf"`, `ACTIVITY_ID = "process-item"`, `process_item(item: str) -> str` activity (heartbeats; fails first 2 attempts, succeeds on the 3rd), `ActivityPauseWorkflow.run(self, item: str) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/workflow_pause/activities_test.py`:

```python
import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.activities import TASK_QUEUE
from workflow_pause.activities.activities import process_item
from workflow_pause.activities.workflow import ActivityPauseWorkflow


async def test_activity_workflow_retries_then_succeeds(
    client: Client, env: WorkflowEnvironment
):
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ActivityPauseWorkflow],
        activities=[process_item],
    ):
        result = await client.execute_workflow(
            ActivityPauseWorkflow.run,
            "widget",
            id=f"activities-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert result == "processed widget"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow_pause/activities_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workflow_pause.activities'`.

- [ ] **Step 3: Create `workflow_pause/activities/__init__.py`**

```python
TASK_QUEUE = "workflow-pause-activities-task-queue"
WORKFLOW_ID = "pause-activities-wf"
ACTIVITY_ID = "process-item"
```

- [ ] **Step 4: Create `workflow_pause/activities/activities.py`**

```python
import asyncio

from temporalio import activity


@activity.defn
async def process_item(item: str) -> str:
    """Long-running activity that heartbeats, and fails its first two attempts.

    The heartbeats + sleep make the activity observably "in flight" so you can
    pause the workflow while it runs. The deliberate failures on the first two
    attempts let you demonstrate `temporal activity pause`, which halts retries.
    """
    info = activity.info()
    activity.logger.info("Processing %s (attempt %d)", item, info.attempt)

    for _ in range(5):
        await asyncio.sleep(1)
        activity.heartbeat()

    if info.attempt < 3:
        raise RuntimeError(f"transient failure on attempt {info.attempt}")

    return f"processed {item}"
```

- [ ] **Step 5: Create `workflow_pause/activities/workflow.py`**

```python
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from workflow_pause.activities import ACTIVITY_ID

with workflow.unsafe.imports_passed_through():
    from workflow_pause.activities.activities import process_item


@workflow.defn
class ActivityPauseWorkflow:
    """Runs a single long-running, retrying activity.

    Two things to demonstrate:
      1. Pausing the *workflow* while the activity is in flight: the running
         activity attempt is not killed, but once it finishes the next workflow
         task is not dispatched, so the workflow does not advance until unpause.
      2. Pausing the *activity* with `temporal activity pause`: retries stop
         after the current attempt ends, and resume on `temporal activity unpause`.
    """

    @workflow.run
    async def run(self, item: str) -> str:
        return await workflow.execute_activity(
            process_item,
            item,
            activity_id=ACTIVITY_ID,
            start_to_close_timeout=timedelta(seconds=30),
            heartbeat_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=3),
                backoff_coefficient=2.0,
                maximum_attempts=10,
            ),
        )
```

- [ ] **Step 6: Create `workflow_pause/activities/worker.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from workflow_pause.activities import TASK_QUEUE
from workflow_pause.activities.activities import process_item
from workflow_pause.activities.workflow import ActivityPauseWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ActivityPauseWorkflow],
        activities=[process_item],
    ):
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
```

- [ ] **Step 7: Create `workflow_pause/activities/starter.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.activities import ACTIVITY_ID, TASK_QUEUE, WORKFLOW_ID
from workflow_pause.activities.workflow import ActivityPauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        ActivityPauseWorkflow.run,
        "widget",
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(f"Pause the workflow:  temporal workflow pause -w {WORKFLOW_ID} --reason demo")
    print(
        f"Pause the activity:  temporal activity pause "
        f"--activity-id {ACTIVITY_ID} -w {WORKFLOW_ID}"
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 8: Create `workflow_pause/activities/README.md`**

````markdown
# Workflow Pause: in-flight activities & activity-level pause

Demonstrates how pause interacts with activities. The workflow runs a single long-running activity
(`process-item`) that heartbeats for ~5 seconds and is configured to fail its first two attempts
before succeeding, so you can observe both kinds of pause.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

    uv run workflow_pause/activities/worker.py

Start the workflow in a second terminal:

    uv run workflow_pause/activities/starter.py

## Demo A — pause the workflow while the activity is in flight

While the worker log shows the activity processing (attempt 1), pause the workflow:

    temporal workflow pause -w pause-activities-wf --reason demo

The currently running activity attempt is **not** killed — it runs to its conclusion — but because
the workflow is paused, the next workflow task is not dispatched, so the workflow does not advance.
Unpause to let it continue:

    temporal workflow unpause -w pause-activities-wf

## Demo B — pause the activity (halt retries)

The activity fails its first two attempts, so it enters a retry backoff. Pause the **activity** so
its retries stop:

    temporal activity pause --activity-id process-item -w pause-activities-wf

The activity will not be retried while paused. Resume retries with:

    temporal activity unpause --activity-id process-item -w pause-activities-wf

On the third attempt the activity succeeds and the workflow completes with `processed widget`.
````

- [ ] **Step 9: Run the test to verify it passes**

Run: `uv run pytest tests/workflow_pause/activities_test.py -v`
Expected: PASS (1 passed). Note: the test exercises the retry-then-succeed path; it does not pause (pause is validated manually per the README).

- [ ] **Step 10: Verify (no commit — user batches commits at end)**

Run the test, confirm green.

---

### Task 3: `signals` — signals buffered while paused

**Files:**
- Create: `workflow_pause/signals/__init__.py`
- Create: `workflow_pause/signals/workflow.py`
- Create: `workflow_pause/signals/worker.py`
- Create: `workflow_pause/signals/starter.py`
- Create: `workflow_pause/signals/README.md`
- Test: `tests/workflow_pause/signals_test.py`

**Interfaces:**
- Produces: `TASK_QUEUE = "workflow-pause-signals-task-queue"`, `WORKFLOW_ID = "pause-signals-wf"`, `SignalPauseWorkflow.run(self) -> list[str]` (runs until a `"done"` signal arrives, returns all received messages), `add_message(self, message: str)` signal, `messages(self) -> list[str]` query.

- [ ] **Step 1: Write the failing test**

Create `tests/workflow_pause/signals_test.py`:

```python
import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.signals import TASK_QUEUE
from workflow_pause.signals.workflow import SignalPauseWorkflow


async def test_signals_collected_then_done(client: Client, env: WorkflowEnvironment):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[SignalPauseWorkflow]):
        handle = await client.start_workflow(
            SignalPauseWorkflow.run,
            id=f"signals-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        await handle.signal(SignalPauseWorkflow.add_message, "hello")
        await handle.signal(SignalPauseWorkflow.add_message, "world")
        await handle.signal(SignalPauseWorkflow.add_message, "done")
        result = await handle.result()
        assert result == ["hello", "world"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow_pause/signals_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workflow_pause.signals'`.

- [ ] **Step 3: Create `workflow_pause/signals/__init__.py`**

```python
TASK_QUEUE = "workflow-pause-signals-task-queue"
WORKFLOW_ID = "pause-signals-wf"
```

- [ ] **Step 4: Create `workflow_pause/signals/workflow.py`**

```python
from temporalio import workflow


@workflow.defn
class SignalPauseWorkflow:
    """Collects messages delivered by signal until a "done" signal arrives.

    Signals sent while the workflow is paused are accepted and recorded in
    history, but the signal handler does not run until the workflow is
    unpaused — at which point the buffered signals are processed in order.
    """

    def __init__(self) -> None:
        self._messages: list[str] = []
        self._done = False

    @workflow.run
    async def run(self) -> list[str]:
        await workflow.wait_condition(lambda: self._done)
        return self._messages

    @workflow.signal
    async def add_message(self, message: str) -> None:
        if message == "done":
            self._done = True
            return
        workflow.logger.info("Received message: %s", message)
        self._messages.append(message)

    @workflow.query
    def messages(self) -> list[str]:
        return self._messages
```

- [ ] **Step 5: Create `workflow_pause/signals/worker.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from workflow_pause.signals import TASK_QUEUE
from workflow_pause.signals.workflow import SignalPauseWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(client, task_queue=TASK_QUEUE, workflows=[SignalPauseWorkflow]):
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
```

- [ ] **Step 6: Create `workflow_pause/signals/starter.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.signals import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.signals.workflow import SignalPauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        SignalPauseWorkflow.run,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(f"Pause it with:    temporal workflow pause -w {WORKFLOW_ID} --reason demo")
    print(
        f'Signal it with:   temporal workflow signal -w {WORKFLOW_ID} '
        f'--name add_message --input \'"hello"\''
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Create `workflow_pause/signals/README.md`**

````markdown
# Workflow Pause: signals are buffered while paused

A signal sent to a **paused** workflow is accepted and recorded in history, but its handler does not
run until the workflow is **unpaused** — then the buffered signals are processed in order.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

    uv run workflow_pause/signals/worker.py

Start the workflow in a second terminal:

    uv run workflow_pause/signals/starter.py

Pause the workflow:

    temporal workflow pause -w pause-signals-wf --reason demo

Now send a signal while paused — it succeeds (it is recorded in history):

    temporal workflow signal -w pause-signals-wf --name add_message --input '"hello"'

But the handler has **not** run yet. Confirm by querying once unpaused (queries are rejected while
paused — see the `queries` sample). Unpause:

    temporal workflow unpause -w pause-signals-wf

The worker now logs `Received message: hello` — the buffered signal was processed on unpause.
Send a `"done"` signal to let the workflow complete:

    temporal workflow signal -w pause-signals-wf --name add_message --input '"done"'
````

- [ ] **Step 8: Run the test to verify it passes**

Run: `uv run pytest tests/workflow_pause/signals_test.py -v`
Expected: PASS (1 passed).

- [ ] **Step 9: Verify (no commit — user batches commits at end)**

Run the test, confirm green.

---

### Task 4: `queries` — queries rejected while paused

**Files:**
- Create: `workflow_pause/queries/__init__.py`
- Create: `workflow_pause/queries/workflow.py`
- Create: `workflow_pause/queries/worker.py`
- Create: `workflow_pause/queries/starter.py`
- Create: `workflow_pause/queries/README.md`
- Test: `tests/workflow_pause/queries_test.py`

**Interfaces:**
- Produces: `TASK_QUEUE = "workflow-pause-queries-task-queue"`, `WORKFLOW_ID = "pause-queries-wf"`, `QueryPauseWorkflow.run(self, iterations: int) -> int`, `current_count(self) -> int` query.

- [ ] **Step 1: Write the failing test**

Create `tests/workflow_pause/queries_test.py`:

```python
import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.queries import TASK_QUEUE
from workflow_pause.queries.workflow import QueryPauseWorkflow


async def test_query_returns_count(client: Client, env: WorkflowEnvironment):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[QueryPauseWorkflow]):
        result = await client.execute_workflow(
            QueryPauseWorkflow.run,
            2,
            id=f"queries-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert result == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow_pause/queries_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workflow_pause.queries'`.

- [ ] **Step 3: Create `workflow_pause/queries/__init__.py`**

```python
TASK_QUEUE = "workflow-pause-queries-task-queue"
WORKFLOW_ID = "pause-queries-wf"
```

- [ ] **Step 4: Create `workflow_pause/queries/workflow.py`**

```python
from datetime import timedelta

from temporalio import workflow


@workflow.defn
class QueryPauseWorkflow:
    """A loop exposing its progress via a query.

    Queries succeed while the workflow is running, but are REJECTED while it is
    paused with: `query was rejected, workflow has status: Paused`. Unpausing
    makes the workflow queryable again.
    """

    def __init__(self) -> None:
        self._count = 0

    @workflow.run
    async def run(self, iterations: int) -> int:
        for _ in range(iterations):
            await workflow.sleep(timedelta(seconds=3))
            self._count += 1
        return self._count

    @workflow.query
    def current_count(self) -> int:
        return self._count
```

- [ ] **Step 5: Create `workflow_pause/queries/worker.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from workflow_pause.queries import TASK_QUEUE
from workflow_pause.queries.workflow import QueryPauseWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(client, task_queue=TASK_QUEUE, workflows=[QueryPauseWorkflow]):
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
```

- [ ] **Step 6: Create `workflow_pause/queries/starter.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.queries import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.queries.workflow import QueryPauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        QueryPauseWorkflow.run,
        20,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(f"Query it with:    temporal workflow query -w {WORKFLOW_ID} --type current_count")
    print(f"Pause it with:    temporal workflow pause -w {WORKFLOW_ID} --reason demo")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Create `workflow_pause/queries/README.md`**

````markdown
# Workflow Pause: queries are rejected while paused

Queries succeed against a running workflow, but are **rejected** while the workflow is paused.
Unpausing makes it queryable again.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

    uv run workflow_pause/queries/worker.py

Start the workflow in a second terminal:

    uv run workflow_pause/queries/starter.py

Query it while running — this returns the current count:

    temporal workflow query -w pause-queries-wf --type current_count

Pause it:

    temporal workflow pause -w pause-queries-wf --reason demo

Query again — it is now **rejected**:

    temporal workflow query -w pause-queries-wf --type current_count
    # Error: query was rejected, workflow has status: Paused

Unpause it and the query works again:

    temporal workflow unpause -w pause-queries-wf
    temporal workflow query -w pause-queries-wf --type current_count
````

- [ ] **Step 8: Run the test to verify it passes**

Run: `uv run pytest tests/workflow_pause/queries_test.py -v`
Expected: PASS (1 passed).

- [ ] **Step 9: Verify (no commit — user batches commits at end)**

Run the test, confirm green.

---

### Task 5: `updates` — updates rejected while paused

**Files:**
- Create: `workflow_pause/updates/__init__.py`
- Create: `workflow_pause/updates/workflow.py`
- Create: `workflow_pause/updates/worker.py`
- Create: `workflow_pause/updates/starter.py`
- Create: `workflow_pause/updates/README.md`
- Test: `tests/workflow_pause/updates_test.py`

**Interfaces:**
- Produces: `TASK_QUEUE = "workflow-pause-updates-task-queue"`, `WORKFLOW_ID = "pause-updates-wf"`, `UpdatePauseWorkflow.run(self) -> int` (runs until a `finish` update, returns final total), `add(self, amount: int) -> int` update (returns new total), `finish(self) -> None` update, `total(self) -> int` query.

- [ ] **Step 1: Write the failing test**

Create `tests/workflow_pause/updates_test.py`:

```python
import uuid

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.updates import TASK_QUEUE
from workflow_pause.updates.workflow import UpdatePauseWorkflow


async def test_update_accumulates_then_finishes(
    client: Client, env: WorkflowEnvironment
):
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[UpdatePauseWorkflow]):
        handle = await client.start_workflow(
            UpdatePauseWorkflow.run,
            id=f"updates-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        assert await handle.execute_update(UpdatePauseWorkflow.add, 5) == 5
        assert await handle.execute_update(UpdatePauseWorkflow.add, 3) == 8
        await handle.execute_update(UpdatePauseWorkflow.finish)
        assert await handle.result() == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow_pause/updates_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workflow_pause.updates'`.

- [ ] **Step 3: Create `workflow_pause/updates/__init__.py`**

```python
TASK_QUEUE = "workflow-pause-updates-task-queue"
WORKFLOW_ID = "pause-updates-wf"
```

- [ ] **Step 4: Create `workflow_pause/updates/workflow.py`**

```python
from temporalio import workflow


@workflow.defn
class UpdatePauseWorkflow:
    """Maintains a running total adjusted via updates.

    An update issued against a paused workflow is REJECTED immediately with:
    `Workflow is paused. Cannot update the workflow.` Unpausing lets updates be
    admitted and executed again.
    """

    def __init__(self) -> None:
        self._total = 0
        self._finished = False

    @workflow.run
    async def run(self) -> int:
        await workflow.wait_condition(lambda: self._finished)
        return self._total

    @workflow.update
    async def add(self, amount: int) -> int:
        self._total += amount
        workflow.logger.info("Total is now %d", self._total)
        return self._total

    @workflow.update
    async def finish(self) -> None:
        self._finished = True

    @workflow.query
    def total(self) -> int:
        return self._total
```

- [ ] **Step 5: Create `workflow_pause/updates/worker.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from workflow_pause.updates import TASK_QUEUE
from workflow_pause.updates.workflow import UpdatePauseWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(client, task_queue=TASK_QUEUE, workflows=[UpdatePauseWorkflow]):
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
```

- [ ] **Step 6: Create `workflow_pause/updates/starter.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.updates import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.updates.workflow import UpdatePauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        UpdatePauseWorkflow.run,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(
        f"Update it with:   temporal workflow update execute -w {WORKFLOW_ID} "
        f"--name add --input 5"
    )
    print(f"Pause it with:    temporal workflow pause -w {WORKFLOW_ID} --reason demo")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Create `workflow_pause/updates/README.md`**

````markdown
# Workflow Pause: updates are rejected while paused

An update issued against a **paused** workflow is rejected immediately. Unpausing lets updates be
admitted and executed again.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

    uv run workflow_pause/updates/worker.py

Start the workflow in a second terminal:

    uv run workflow_pause/updates/starter.py

Send an update while running — it returns the new total:

    temporal workflow update execute -w pause-updates-wf --name add --input 5

Pause it:

    temporal workflow pause -w pause-updates-wf --reason demo

Send an update while paused — it is **rejected** immediately:

    temporal workflow update execute -w pause-updates-wf --name add --input 5
    # Error: unable to update workflow: Workflow is paused. Cannot update the workflow.

Unpause it and updates work again. Finish the workflow with the `finish` update:

    temporal workflow unpause -w pause-updates-wf
    temporal workflow update execute -w pause-updates-wf --name add --input 3
    temporal workflow update execute -w pause-updates-wf --name finish
````

- [ ] **Step 8: Run the test to verify it passes**

Run: `uv run pytest tests/workflow_pause/updates_test.py -v`
Expected: PASS (1 passed).

- [ ] **Step 9: Verify (no commit — user batches commits at end)**

Run the test, confirm green.

---

### Task 6: `cancel_terminate` — cancel vs terminate on a paused workflow

**Files:**
- Create: `workflow_pause/cancel_terminate/__init__.py`
- Create: `workflow_pause/cancel_terminate/workflow.py`
- Create: `workflow_pause/cancel_terminate/worker.py`
- Create: `workflow_pause/cancel_terminate/starter.py`
- Create: `workflow_pause/cancel_terminate/README.md`
- Test: `tests/workflow_pause/cancel_terminate_test.py`

**Interfaces:**
- Produces: `TASK_QUEUE = "workflow-pause-cancel-terminate-task-queue"`, `WORKFLOW_ID = "pause-cancel-terminate-wf"`, `CancelTerminatePauseWorkflow.run(self, iterations: int) -> str` (loops; on cancellation logs cleanup and returns `"cancelled"`, otherwise returns `"completed"`).

- [ ] **Step 1: Write the failing test**

Create `tests/workflow_pause/cancel_terminate_test.py`:

```python
import asyncio
import uuid

import pytest
from temporalio.client import Client, WorkflowFailureError
from temporalio.exceptions import CancelledError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_pause.cancel_terminate import TASK_QUEUE
from workflow_pause.cancel_terminate.workflow import CancelTerminatePauseWorkflow


async def test_cancellation_runs_cleanup(client: Client, env: WorkflowEnvironment):
    async with Worker(
        client, task_queue=TASK_QUEUE, workflows=[CancelTerminatePauseWorkflow]
    ):
        handle = await client.start_workflow(
            CancelTerminatePauseWorkflow.run,
            20,
            id=f"cancel-terminate-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        # Let the workflow start its loop, then cancel it.
        await asyncio.sleep(1)
        await handle.cancel()
        with pytest.raises(WorkflowFailureError) as exc_info:
            await handle.result()
        assert isinstance(exc_info.value.cause, CancelledError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/workflow_pause/cancel_terminate_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'workflow_pause.cancel_terminate'`.

- [ ] **Step 3: Create `workflow_pause/cancel_terminate/__init__.py`**

```python
TASK_QUEUE = "workflow-pause-cancel-terminate-task-queue"
WORKFLOW_ID = "pause-cancel-terminate-wf"
```

- [ ] **Step 4: Create `workflow_pause/cancel_terminate/workflow.py`**

```python
import asyncio
from datetime import timedelta

from temporalio import workflow


@workflow.defn
class CancelTerminatePauseWorkflow:
    """A loop that runs cleanup logic when cancelled.

    On a PAUSED workflow:
      - `temporal workflow terminate` takes effect immediately.
      - `temporal workflow cancel` records a WorkflowExecutionCancelRequested
        event, but the workflow stays Paused and its cancellation handling (the
        cleanup below) does not run until the workflow is unpaused.
    """

    @workflow.run
    async def run(self, iterations: int) -> str:
        try:
            for i in range(iterations):
                workflow.logger.info("Working, iteration %d", i + 1)
                await workflow.sleep(timedelta(seconds=3))
            return "completed"
        except asyncio.CancelledError:
            workflow.logger.info("Cancellation received — running cleanup")
            raise
```

- [ ] **Step 5: Create `workflow_pause/cancel_terminate/worker.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from workflow_pause.cancel_terminate import TASK_QUEUE
from workflow_pause.cancel_terminate.workflow import CancelTerminatePauseWorkflow

interrupt_event = asyncio.Event()


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    async with Worker(
        client, task_queue=TASK_QUEUE, workflows=[CancelTerminatePauseWorkflow]
    ):
        logging.info("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        logging.info("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
```

- [ ] **Step 6: Create `workflow_pause/cancel_terminate/starter.py`**

```python
import asyncio
import logging

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.envconfig import ClientConfig

from workflow_pause.cancel_terminate import TASK_QUEUE, WORKFLOW_ID
from workflow_pause.cancel_terminate.workflow import CancelTerminatePauseWorkflow


async def main():
    logging.basicConfig(level=logging.INFO)

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    handle = await client.start_workflow(
        CancelTerminatePauseWorkflow.run,
        20,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
        id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
    )
    print(f"Started workflow with ID: {handle.id}")
    print(f"Pause it with:      temporal workflow pause -w {WORKFLOW_ID} --reason demo")
    print(f"Terminate it with:  temporal workflow terminate -w {WORKFLOW_ID}")
    print(f"Cancel it with:     temporal workflow cancel -w {WORKFLOW_ID}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Create `workflow_pause/cancel_terminate/README.md`**

````markdown
# Workflow Pause: cancel vs terminate on a paused workflow

Shows how cancel and terminate differ when a workflow is paused:

- **Terminate** takes effect immediately, even while paused.
- **Cancel** records a `WorkflowExecutionCancelRequested` event, but the workflow stays `Paused` and
  its cancellation handling does not run until you **unpause** it.

> Workflow Pause is experimental. The dev server must be started with the pause flag enabled —
> see the [workflow_pause README](../README.md) for prerequisites. First see the main
> [README.md](../../README.md) for general prerequisites.

Run the worker in one terminal:

    uv run workflow_pause/cancel_terminate/worker.py

## Terminate a paused workflow (immediate)

Start the workflow in a second terminal:

    uv run workflow_pause/cancel_terminate/starter.py

Pause then terminate it — it ends right away:

    temporal workflow pause -w pause-cancel-terminate-wf --reason demo
    temporal workflow terminate -w pause-cancel-terminate-wf
    temporal workflow describe -w pause-cancel-terminate-wf   # Status: Terminated

## Cancel a paused workflow (deferred until unpause)

Start a fresh run (re-running the starter terminates the previous one):

    uv run workflow_pause/cancel_terminate/starter.py

Pause it, then request cancellation:

    temporal workflow pause -w pause-cancel-terminate-wf --reason demo
    temporal workflow cancel -w pause-cancel-terminate-wf

Describe it — the cancel is recorded but the status is still `Paused`:

    temporal workflow describe -w pause-cancel-terminate-wf   # Status: Paused

Unpause it — now the workflow processes the cancellation (the worker logs
"Cancellation received — running cleanup") and ends as `Canceled`:

    temporal workflow unpause -w pause-cancel-terminate-wf
    temporal workflow describe -w pause-cancel-terminate-wf   # Status: Canceled
````

- [ ] **Step 8: Run the test to verify it passes**

Run: `uv run pytest tests/workflow_pause/cancel_terminate_test.py -v`
Expected: PASS (1 passed).

- [ ] **Step 9: Verify (no commit — user batches commits at end)**

Run the test, confirm green.

---

### Task 7: Index README + root README listing + format/lint

**Files:**
- Create: `workflow_pause/README.md`
- Modify: `README.md` (root, `## Samples` list)

- [ ] **Step 1: Create `workflow_pause/README.md`**

````markdown
# Workflow Pause

These samples demonstrate the experimental **Workflow Pause** feature. Pausing a Workflow Execution
tells the Temporal Service to stop dispatching workflow tasks for it — the workflow makes no forward
progress (timers don't advance, signals buffer, queries and updates are rejected) until it is
**unpaused**. See the [Temporal CLI docs](https://docs.temporal.io/cli/workflow#pause).

## Prerequisites

First see the main [README.md](../README.md) for general prerequisites. Then note:

- Requires **Temporal Server 1.31.0+ / CLI 1.7.1+**. The feature is experimental.
- **Pause must be enabled server-side.** Start your dev server with the pause dynamic-config flag:

      temporal server start-dev --dynamic-config-value frontend.WorkflowPauseEnabled=true

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
````

- [ ] **Step 2: Add the workflow_pause entry to the root `README.md`**

In `README.md`, find the `## Samples` list. After the `worker_multiprocessing` line (the last entry, around line 99), add:

```markdown
* [workflow_pause](workflow_pause/) - Demonstrate the experimental Workflow Pause feature: pause/unpause, signals, queries, updates, activities, and cancel/terminate.
```

Verify placement:

Run: `grep -n "workflow_pause" README.md`
Expected: one new line under the `## Samples` section.

- [ ] **Step 3: Format and lint**

Run: `uv run poe format && uv run poe lint`
Expected: formatting applied cleanly, lint passes. Fix any issues reported for files under `workflow_pause/` and `tests/workflow_pause/`.

- [ ] **Step 4: Run the full workflow_pause test suite**

Run: `uv run pytest tests/workflow_pause -v`
Expected: 6 passed.

- [ ] **Step 5: Verify (no commit — user batches commits at end)**

Confirm the full suite is green and report completion to the user. The user will handle all git commits.

---

## Manual end-to-end verification (after implementation, optional but recommended)

With a dev server running with the pause flag enabled, run through each sample's README CLI
walkthrough once to confirm the observable behavior matches the documented behavior:

```bash
temporal server start-dev --dynamic-config-value frontend.WorkflowPauseEnabled=true
```

Then for each sample: start worker, run starter, execute the README's pause/unpause/signal/query/
update/cancel/terminate commands, and confirm outputs match.

## Self-Review Notes

- **Spec coverage:** basic (Task 1), activities + activity pause (Task 2), signals (Task 3),
  queries (Task 4), updates (Task 5), cancel/terminate (Task 6), index + root README (Task 7),
  empirically-verified behaviors reflected in every README. All spec sections covered.
- **No placeholders:** every file's full contents are inlined.
- **Type consistency:** `TASK_QUEUE`/`WORKFLOW_ID`/`ACTIVITY_ID` constants and workflow
  method names are referenced identically across `__init__.py`, `worker.py`, `starter.py`,
  `workflow.py`, and tests within each sample.
- **Commits:** deliberately omitted per the user's instruction to batch commits at the end.
