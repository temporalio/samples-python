# Update With Start: Early return

This sample uses Update-with-Start to start payment processing and return its
authorization result before the Workflow finishes. The client can move on after
authorization while Temporal continues the slower capture step.

To run, first see the main [README.md](../../../README.md) for prerequisites.

Then run the following from the root directory:

    uv run message_passing/update_with_start/early_return/worker.py

In another terminal, run:

    uv run message_passing/update_with_start/early_return/starter.py

The starter returns after authorization. The worker logs the capture later, when
the Workflow completes.
