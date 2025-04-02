# Periodic Polling of a Sequence of Activities

This sample demonstrates how to use a Child Workflow for periodic Activity polling.

This is a rare scenario where polling requires execution of a Sequence of Activities, or Activity arguments need to change between polling retries. For this case we use a Child Workflow to call polling activities a set number of times in a loop and then periodically call Continue-As-New.

To run, first see [README.md](../../README.md) for prerequisites.

Then, run the following from this directory to run the sample:

    uv run run_worker.py

Then, in another terminal, run the following to execute the workflow:

    uv run run_periodic.py


This will start a Workflow and Child Workflow to periodically poll an Activity.
The Parent Workflow is not aware about the Child Workflow calling Continue-As-New, and it gets notified when it completes (or fails).