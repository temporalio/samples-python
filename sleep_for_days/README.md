# Sleep for Days

This sample demonstrates how to create a Temporal workflow that runs forever, sending an email every 30 days.

To run, first see the main [README.md](../../README.md) for prerequisites.

Then create two terminals and `cd` to this directory.

Run the worker in one terminal:

    poetry run python worker.py

And execute the workflow in the other terminal:

    poetry run python starter.py

This sample will run indefinitely until you send a signal to `complete`. See how to send a signal via Temporal CLI [here](https://docs.temporal.io/cli/workflow#signal).

