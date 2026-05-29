# Custom Worker Tuner

A `CustomSlotSupplier` is a sample that lets you gate slot grants on whatever you want.
This sample gates on a fake DB pool: the worker only polls for a new
activity when the pool has a free connection.

**Note:** This sample is illustrative only. It shouldn't be used for production grade use-cases.

## What this sample is
db_pool.py - A fixed-capacity fake pool backed by a `BoundedSemaphore`. Two methods: `acquire(blocking=True)` (claim a slot, returns False if full when non-blocking), `release()` (return a slot)
supplier.py - The custom slot supplier. `reserve_slot` blocks on `connection_pool.acquire()` until a slot is free; `try_reserve_slot` does the same non-blocking. `release_slot` calls `connection_pool.release()`
shared.py - A RunBatch workflow that runs N do_work activities in parallel. The activity just sleeps
worker.py - Wires `FakeDatabaseConnectionPool` + `PoolSlotSupplier` into a WorkerTuner
starter.py - Drives load

The flow:

When the pool is at capacity, `reserve_slot` blocks until a
connection frees up. The excess work piles up on the Temporal server, not
inside the worker.

## Run

In three terminals from `samples-python/`:

```bash
temporal server start-dev                       # terminal 1
uv run custom_worker_tuner/worker.py            # terminal 2
uv run custom_worker_tuner/starter.py           # terminal 3
```

## What you'll see

The worker prints one line per slot lifecycle event:

```
TIME          EVENT     COUNT     QUEUE  DETAIL
(COUNT shows before→after / capacity; QUEUE = tasks parked waiting)
─────────────────────────────────────────────────────────────────
12:30:32.591  reserve    0→ 1/10      0  ready to poll
12:30:32.591  reserve    1→ 2/10      0  ready to poll
12:30:32.592  reserve    2→ 3/10      0  ready to poll
12:30:32.592  reserve    3→ 4/10      0  ready to poll
12:30:32.592  reserve    4→ 5/10      0  ready to poll
12:30:32.592  reserve    5→ 6/10      0  ready to poll
12:30:40.501  reserve    6→ 7/10      0  eager dispatch
12:30:40.502  reserve    7→ 8/10      0  eager dispatch
12:30:40.502  reserve    8→ 9/10      0  eager dispatch
12:30:40.505  release    9→ 8/10      0  no task arrived
12:30:40.506  release    8→ 7/10      0  no task arrived
12:30:40.506  release    7→ 6/10      0  no task arrived
12:30:40.510  used       6→ 6/10      0  activity running
12:30:40.510  reserve    6→ 7/10      0  eager dispatch
12:30:40.511  reserve    7→ 8/10      0  eager dispatch
12:30:40.511  reserve    8→ 9/10      0  eager dispatch
12:30:40.514  reserve    9→10/10      0  ready to poll
12:30:40.520  release   10→ 9/10      0  no task arrived
12:30:40.520  release    9→ 8/10      0  no task arrived
12:30:40.520  release    8→ 7/10      0  no task arrived
12:30:40.520  used       7→ 7/10      0  activity running
12:30:40.520  reserve    7→ 8/10      0  eager dispatch
12:30:40.520  reserve    8→ 9/10      0  eager dispatch
12:30:40.520  reserve    9→10/10      0  eager dispatch
12:30:40.525  release   10→10/10      0  no task arrived
12:30:40.525  release   10→ 9/10      0  no task arrived
12:30:40.525  release    9→ 8/10      0  no task arrived
12:30:40.528  reserve    7→ 8/10      0  ready to poll
12:30:40.530  used       8→ 8/10      0  activity running
12:30:40.535  reserve    8→ 9/10      0  eager dispatch
12:30:40.537  reserve    9→10/10      0  eager dispatch
12:30:40.539  used      10→10/10      1  activity running
12:30:40.540  used      10→10/10      1  activity running
12:30:40.541  used      10→10/10      1  activity running
```

Under load, with more activities than capacity, COUNT pins at
10/10 — that's the supplier refusing to poll past the gate.
we chose 10 because default there are 5 pollers for python sdk 

## Knobs

worker.py:

CAPACITY — pool capacity (the gate)

starter.py:

WORKFLOWS, ACTIVITIES_PER_WORKFLOW, SECONDS_PER_ACTIVITY — amount and duration of load
