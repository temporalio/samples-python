# Atomic message handlers

This sample shows off important techniques for handling signals and updates, aka messages.  In particular, it illustrates how message handlers can interleave or not be completed before the workflow completes, and how you can manage that.

* Here, using workflow.wait_condition, signal and update handlers will only operate when the workflow is within a certain state--between cluster_started and cluster_shutdown.
* You can run start_workflow with an initializer signal that you want to run before anything else other than the workflow's constructor.  This pattern is known as "signal-with-start."
* Message handlers can block and their actions can be interleaved with one another and with the main workflow.  This can easily cause bugs, so we use a lock to protect shared state from interleaved access.
* Message handlers should also finish before the workflow run completes.  One option is to use a lock.
* An "Entity" workflow, i.e. a long-lived workflow, periodically "continues as new".  It must do this to prevent its history from growing too large, and it passes its state to the next workflow.  You can check `workflow.info().is_continue_as_new_suggested()` to see when it's time.  Just make sure message handlers have finished before doing so.  
* Message handlers can be made idempotent.  See update `ClusterManager.assign_nodes_to_job`.

To run, first see [README.md](../../README.md) for prerequisites.

Then, run the following from this directory to run the worker:
\
    poetry run python worker.py

Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

This will start a worker to run your workflow and activities, then start a ClusterManagerWorkflow and put it through its paces.
