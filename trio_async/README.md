# Trio Async Sample

This sample shows how to use Temporal asyncio with [Trio](https://trio.readthedocs.io) using
[Trio asyncio](https://trio-asyncio.readthedocs.io). Specifically it demonstrates using a traditional Temporal client
and worker in a Trio setting, and how Trio-based code can run in both asyncio async activities and threaded sync
activities.

This sample requires Python 3.12 or 3.13 and `temporalio` <= 1.36.1. It is a
standalone uv project pinned to 1.36.1. Starting with 1.37.0, the SDK calls
`TrioExecutor.submit()` directly and expects a `concurrent.futures.Future`,
but Trio's executor returns a coroutine.

Start a local Temporal dev server as described in the [root README](../README.md).
From the repository root, change to the sample directory and install its dependencies:

    cd trio_async
    uv sync

Start the worker from the `trio_async` directory:

    uv run worker.py

In another terminal, also from the `trio_async` directory, execute the workflow:

    uv run starter.py

The starter should complete with:

    INFO:root:Workflow result: ['Hello, Temporal! (from asyncio)', 'Hello, Temporal! (from thread)']

Run the sample tests from the same directory with `uv run poe test`.
