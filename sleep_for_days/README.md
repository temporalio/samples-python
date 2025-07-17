# Sleep for Days

This sample demonstrates how to create a Temporal workflow that runs forever, sending an email every 30 days.

To run, first see the main [README.md](../../README.md) for prerequisites.

Then create two terminals.

Run the worker in one terminal:

    uv run sleep_for_days/worker.py

And execute the workflow in the other terminal:

    uv run sleep_for_days/starter.py

This sample will run indefinitely until you send a signal to `complete`. See how to send a signal via Temporal CLI [here](https://docs.temporal.io/cli/workflow#signal).

