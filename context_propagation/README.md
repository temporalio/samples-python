# Context Propagation Interceptor Sample

This sample shows how to use an interceptor to propagate contextual information through workflows and activities. For
this example, [contextvars](https://docs.python.org/3/library/contextvars.html) holds the contextual information.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The starter terminal should complete with the hello result and the worker terminal should show the logs with the
propagated user ID contextual information flowing through the workflows/activities.