# Streams on Redis

> **Experimental.** The Streams SDK and Redis Store are unreleased. Their APIs can change.

This sample reads agent events from Redis after a client disconnects.
The reader resumes after its last consumed offset.

Update-with-Start starts the Workflow and requests its `StreamRef` in one call.
The Activity uses `BufferedAppender` to write fixed model tokens without an external model service.
A `Done` event stops the reader. The Workflow result reports success or failure.
On cancellation, the Workflow waits for its Activity to stop before writing `Done`.
The client also observes the result because termination can prevent that final event.

Streams have no close operation. Each new batch restarts retention, which defaults to seven days.
Reads and resends do not extend retention. Events remain readable until retention expires.
The [Workflow Streams sample](../workflow_streams) keeps events in the Workflow and needs no Store.

## Install

Install Redis 7.0 or later, Rust and `protoc`. Run these commands from the repository root.

```bash
uv sync
uv pip install "temporalio @ git+https://github.com/temporalio/sdk-python@moe/streams-api"
git clone --branch moe/retention-from-close \
  https://github.com/temporal-community/sdk-streams ../sdk-streams
(cd ../sdk-streams && SDK_RUST_REF=moe/streams-crate-types scripts/patch-sdk-rust.sh)
uv pip install ../sdk-streams/python
```

The patch script selects the unreleased `temporalio-streams` Rust crate.
Use `--no-sync` below to keep `uv` from replacing these packages with released versions.

## Run

Start Redis and Temporal in separate terminals.

```bash
redis-server --port 26379
```

```bash
temporal server start-dev
```

Start the Worker and client in separate terminals.

```bash
REDIS_URL=redis://localhost:26379 uv run --no-sync streams_redis/run_worker.py
```

```bash
REDIS_URL=redis://localhost:26379 uv run --no-sync streams_redis/run_agent.py
```

The client prints each event and its offset.
After four events, it reconnects and reads through `Done`.
Activity retries can append repeated tokens at new offsets.
A Workflow failure ends the reader and raises the Workflow error.

## Test

The tests start a local Temporal server and a private `redis-server` from `PATH`.
Collection skips these tests when either unreleased package is absent.

```bash
uv run --no-sync pytest tests/streams_redis
```
