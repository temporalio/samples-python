# Custom Decorator Sample

This sample shows a custom decorator can help with Temporal code reuse. Specifically, this makes a `@auto_heartbeater`
decorator that automatically configures an activity to heartbeat twice as frequently as the heartbeat timeout is set to.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The workflow will be started, and then after 5 seconds will be sent a signal to cancel its forever-running activity.
The activity has a heartbeat timeout set to 2s, so since it has the `@auto_heartbeater` decorator set, it will heartbeat
every second. If this was not set, the workflow would fail with an activity heartbeat timeout failure.