# Workflow Update Sample

This sample shows you how you can end a request to and a response from a client to a workflow execution.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute a workflow:

    poetry run python starter.py

Which should produce some output like:

    Update Result: Workflow status updated
    Workflow Result: Hello, World!

Note: To enable the workflow update, set the `frontend.enableUpdateWorkflowExecution` dynamic config value to true.

    temporal server start-dev --dynamic-config-value frontend.enableUpdateWorkflowExecution=true