# Waiting for message handlers, and performing compensation and cleanup in message handlers

This sample demonstrates the following recommended practices:

1. Ensuring that all signal and update handlers are finished before a successful
    workflow return, and on workflow failure, cancellation, and continue-as-new.
2. Performing necessary compensation/cleanup in an update handler when the
    workflow is cancelled, fails, or continues-as-new.


To run, open two terminals and `cd` to this directory in them.

Run the worker in one terminal:

    poetry run python worker.py

And run the workflow-starter code in the other terminal:

    poetry run python starter.py


Here's the output you'll see, along with some explanation:

```
workflow exit type: success
  update action on premature workflow exit: continue
    👇 [Caller gets a successful update response because main workflow method waits for handlers to finish]
    🟢 caller received update result
    🟢 caller received workflow result
  update action on premature workflow exit: abort_with_compensation
    👇 [Same as above: the workflow is successful for action-on-premature exit is irrelevant]
    🟢 caller received update result
    🟢 caller received workflow result


workflow exit type: failure
  update action on premature workflow exit: continue
    👇 [update does not abort and main workflow method waits for handlers to finish => caller gets successful update result prior to workflow failure]
    🟢 caller received update result
    🔴 caught exception while waiting for workflow result: Workflow execution failed: deliberately failing workflow
  update action on premature workflow exit: abort_with_compensation
    👇 [update aborts, compensates and raises => caller gets failed update result]
    🔴 caught exception while waiting for update result: Workflow update failed: The update failed because the workflow run exited: deliberately failing workflow
    🔴 caught exception while waiting for workflow result: Workflow execution failed: deliberately failing workflow


workflow exit type: cancellation
  update action on premature workflow exit: continue
    👇 [update does not abort and main workflow method waits for handlers to finish => caller gets successful update result prior to workflow cancellation]
    🟢 caller received update result
    🔴 caught exception while waiting for workflow result: Workflow execution failed: Workflow cancelled
  update action on premature workflow exit: abort_with_compensation
    👇 [update aborts, compensates and raises => caller gets failed update result]
    🔴 caught exception while waiting for update result: Workflow update failed: The update failed because the workflow run exited:
    🔴 caught exception while waiting for workflow result: Workflow execution failed: Workflow cancelled


workflow exit type: continue_as_new
  update action on premature workflow exit: continue
    👇 [update does not abort and main workflow method waits for handlers to finish => caller gets successful update result prior to continue-as-new]
    🟢 caller received update result
    👇 [a second update is sent to the post-CAN run, which run succeeds, hence update succeeds]
    🟢 caller received update result
    🟢 caller received workflow result
  update action on premature workflow exit: abort_with_compensation
    👇 [update aborts, compensates and raises => caller gets failed update result]
    🔴 caught exception while waiting for update result: update "50cd58dc-2db7-4a70-9204-bf5922203203" not found:
    👇 [a second update is sent to the post-CAN run, which run succeeds, hence update succeeds]
    🟢 caller received update result
    🟢 caller received workflow result
```