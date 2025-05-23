# Waiting for message handlers

This workflow demonstrates how to wait for signal and update handlers to
finish in the following circumstances:

- Before a successful return
- On failure
- On cancellation

Your workflow can also exit via Continue-As-New. In that case you would
usually wait for the handlers to finish immediately before the call to
continue_as_new(); that's not illustrated in this sample.


To run, open two terminals and `cd` to this directory in them.

Run the worker in one terminal:

    uv run worker.py

And run the workflow-starter code in the other terminal:

    uv run starter.py


Here's the output you'll see:

```
workflow exit type: SUCCESS
    🟢 caller received update result
    🟢 caller received workflow result


workflow exit type: FAILURE
    🟢 caller received update result
    🔴 caught exception while waiting for workflow result: Workflow execution failed: deliberately failing workflow


workflow exit type: CANCELLATION
    🟢 caller received update result
```