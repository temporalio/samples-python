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

TIME          EVENT     SLOT     COUNT   DETAIL
────────────────────────────────────────────────────────────
10:31:49.842  reserve   #1      1/10  ready to poll
10:31:49.842  reserve   #2      2/10  ready to poll
10:31:49.843  reserve   #3      3/10  ready to poll
10:31:49.843  reserve   #4      4/10  ready to poll
10:31:49.843  reserve   #5      5/10  ready to poll
10:31:49.843  reserve   #6      6/10  ready to poll
10:31:56.763  reserve   #7      7/10  eager dispatch
10:31:56.763  reserve   #8      8/10  eager dispatch
10:31:56.764  reserve   #9      9/10  eager dispatch
10:31:56.766  reserve   #10    10/10  eager dispatch
10:31:56.767  release   #7      9/10  no task arrived
10:31:56.768  release   #8      8/10  no task arrived
10:31:56.768  release   #9      7/10  no task arrived
10:31:56.768  reserve   #11     8/10  eager dispatch
10:31:56.768  reserve   #12     9/10  eager dispatch
10:31:56.768  reserve   #13    10/10  eager dispatch
10:31:56.771  used      #1     10/10  activity running
10:31:56.771  release   #10     9/10  no task arrived
```

Under load, with more activities than capacity, COUNT pins at
10/10 — that's the supplier refusing to poll past the gate.
we chose 10 because default there are 5 pollers for python sdk 

## Knobs

worker.py:

CAPACITY — pool capacity (the gate)

starter.py:

WORKFLOWS, ACTIVITIES_PER_WORKFLOW, SECONDS_PER_ACTIVITY — amount and duration of load
