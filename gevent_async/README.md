# Gevent Sample

This sample shows how to run Temporal in an environment that gevent has patched.

Gevent is built to patch Python libraries to attempt to seamlessly convert threaded code into coroutine-based code.
However, it is well known within the gevent community that it does not work well with `asyncio`, which is the modern
Python approach to coroutines. Temporal leverages `asyncio` which means by default it is incompatible with gevent. Users
are encouraged to abandon gevent in favor of more modern approaches where they can but it is not always possible.

This sample shows how to use a customized gevent executor to run `asyncio` Temporal clients, workers, activities, and
workflows.

For this sample, the optional `gevent` dependency group must be included. To include, run:

    uv sync --group gevent

To run the sample, first see [README.md](../README.md) for prerequisites such as having a localhost Temporal server
running. Then, run the following from the root directory to start the worker:

    uv run gevent_async/worker.py

This will start the worker. The worker has a workflow and two activities, one `asyncio` based and one gevent based. Now
in another terminal, run the following to execute the workflow:

    uv run gevent_async/starter.py

The workflow should run and complete with the hello result. Note on the worker terminal there will be logs of the
workflow and activity executions.