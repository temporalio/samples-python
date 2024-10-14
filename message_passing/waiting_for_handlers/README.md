# Waiting for message handlers, and performing compensation and cleanup in message handlers

This sample demonstrates how to do the following:

1. Ensure that all update/signal handlers are finished before a successful
    workflow return, and on workflow cancellation and failure.
2. Perform compensation/cleanup in an update handler when the workflow is
    cancelled or fails.



To run, open two terminals and `cd` to this directory in them.

Run the worker in one terminal:

    poetry run python worker.py

And run the workflow-starter code in the other terminal:

    poetry run python starter.py


Here's the output you'll see:

```
workflow exit type: SUCCESS
    🟢 caller received update result
    🟢 caller received workflow result


workflow exit type: FAILURE
    🔴 caught exception while waiting for update result: Workflow update failed: The update failed because the workflow run exited
    🔴 caught exception while waiting for workflow result: Workflow execution failed: deliberately failing workflow


workflow exit type: CANCELLATION
    🔴 caught exception while waiting for update result: Workflow update failed: The update failed because the workflow run exited
    🔴 caught exception while waiting for workflow result: Workflow execution failed: Workflow cancelled
```