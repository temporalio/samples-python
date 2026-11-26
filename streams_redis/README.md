# Streams on Redis

> **Experimental.** This sample uses the Streams API of the Temporal Python SDK and the
> Redis Stream Store of `temporal-community/sdk-streams`. Neither has a release yet, and
> both APIs may change.

A Stream is an append-only log of events in a Stream Store, here Redis. Workflow code,
Activities and clients append to it, and a reader goes on from the offset of the last event
that it read. `temporalio.contrib.workflow_streams` (see
[workflow_streams](../workflow_streams)) keeps its events in the Workflow and needs no
Store. A Stream keeps them in Redis. A client reads them from there, and they stay
readable after the Workflow ends. A Stream has no close. It expires when its Retention
(7 days by default) passes with no append.

The sample has one scenario:

* `workflows/agent_workflow.py` - an agent-like Workflow. It creates a Stream with the id
  of the Workflow, writes a status event, and runs the model Activity. In `finally` it
  writes the status event `Done`, which tells a reader to stop.
* `activities/model_activity.py` - an Activity that stands in for a model. It appends each
  token of its answer to the Stream with `BufferedAppender`.
* `run_agent.py` - starts the Workflow, gets the `StreamRef` from an Update, and prints the
  events as they come. After four events it disconnects. A new client then reads on from
  the offset of the last event that it printed, and stops at `Done`. A read never ends
  by itself, so each reader breaks out of its loop. A terminated Workflow writes no
  `Done`, so its reader waits until you stop it.

## Install

The two packages build from source, with Rust and `protoc`. From the root of this repo:

```bash
uv sync
uv pip install "temporalio @ git+https://github.com/temporalio/sdk-python@moe/streams-api"
git clone --branch moe/retention-from-close https://github.com/temporal-community/sdk-streams ../sdk-streams
(cd ../sdk-streams && SDK_RUST_REF=moe/streams-crate-types scripts/patch-sdk-rust.sh)
uv pip install ../sdk-streams/python
```

The Store's native module needs the crate `temporalio-streams`, which isn't on crates.io
yet. `patch-sdk-rust.sh` points the build at the branch of `temporalio/sdk-rust` that has it.

## Run it

Start Redis and a Temporal dev server:

```bash
redis-server
temporal server start-dev
```

Start the Worker, and then the agent in another terminal:

```bash
uv run --no-sync streams_redis/run_worker.py
uv run --no-sync streams_redis/run_agent.py
```

`--no-sync` keeps uv from putting the released `temporalio` back. Set `REDIS_URL` for a
Redis other than `redis://localhost:6379`.

The agent prints each event with its offset, which is opaque bytes:

```
000001a2068b96180000000000000000  status  Thinking about: Why keep the events of an agent in Redis?
000001a2068b96880000000000000000  token   Redis
000001a2068b97210000000000000000  token   keeps
000001a2068b97b90000000000000000  token   the
-- The reader disconnects, and the agent goes on.
000001a2068b98510000000000000000  token   events,
...
000001a2068b9edd0000000000000000  token   rest.
000001a2068b9f120000000000000000  status  Done
-- The Workflow returned: Redis keeps the events, so a reader can leave and come back for the rest.
```

## Test

The test starts its own `redis-server`, from the `PATH`. It isn't collected when the two
packages aren't installed, as in the CI of this repo.

```bash
uv run --no-sync pytest tests/streams_redis
```
