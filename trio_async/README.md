# Trio Async Sample

This sample shows how to use Temporal asyncio with [Trio](https://trio.readthedocs.io) using
[Trio asyncio](https://trio-asyncio.readthedocs.io). Specifically it demonstrates using a traditional Temporal client
and worker in a Trio setting, and how Trio-based code can run in both asyncio async activities and threaded sync
activities.

For this sample, the optional `trio_async` dependency group must be included. To include, run:

    uv sync --group trio_async

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from the root directory to start the
worker:

    uv run trio_async/worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    uv run trio_async/starter.py

The starter should complete with:

    INFO:root:Workflow result: ['Hello, Temporal! (from asyncio)', 'Hello, Temporal! (from thread)']