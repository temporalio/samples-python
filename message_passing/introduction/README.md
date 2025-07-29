# Introduction to message-passing

This sample provides an introduction to using Query, Signal, and Update.

See https://docs.temporal.io/develop/python/message-passing.

To run, first see the main [README.md](../../README.md) for prerequisites.

Then create two terminals.

Run the worker in one terminal:

    uv run message_passing/introduction/worker.py

And execute the workflow in the other terminal:

    uv run message_passing/introduction/starter.py

