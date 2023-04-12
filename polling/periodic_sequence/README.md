# Periodic Child Workflow Retry

This sample demonstrates how to use a Child Workflow for periodic activity polling.

This is a rare scenario where polling requires execution of a sequence of activities, or activity arguments need to change between polling retries. For this case we use a Child Workflow to call polling activities a set number of times in a loop and then periodically call continue-as-new.

To run, first see [README.md](../README.md) for prerequisites.

Then, run the following from this directory to run the sample:

```bash
poetry run python run_worker.py
poetry run python run_periodic.py
```

This will start a Workflow and Child Workflow to periodically poll an activity.
The Parent Workflow is not aware about the Child Workflow calling continue-as-new, and it gets notified when it completes (or fails).