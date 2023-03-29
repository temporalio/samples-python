# Prometheus Sample

This sample shows how to have SDK Prometheus metrics made available via HTTP.

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    poetry run python worker.py

This will start the worker and the metrics will be visible for this process at http://127.0.0.1:9000/metrics.

Then, in another terminal, run the following to execute a workflow:

    poetry run python starter.py

After executing the workflow, the process will stay open so the metrics if this separate process can be accessed at
http://127.0.0.1:9001/metrics.