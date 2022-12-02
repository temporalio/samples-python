# Sentry Sample

This sample shows how to configure [Sentry](https://sentry.io) to intercept and capture errors from the Temporal SDK.

For this sample, the optional `sentry` dependency group must be included. To include, run:

    poetry install --with sentry

To run, first see [README.md](../README.md) for prerequisites. Set `SENTRY_DSN` environment variable to the Sentry DSN.
Then, run the following from this directory to start the worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The workflow should complete with the hello result. If you alter the workflow or the activity to raise an
`ApplicationError` instead, it should appear in Sentry.