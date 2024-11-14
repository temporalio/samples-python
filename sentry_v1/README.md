# Sentry Sample

This sample shows how to configure [Sentry](https://sentry.io) to intercept and capture errors from the Temporal SDK.

> Note: This example uses Sentry SDK v1 which is now deprecated. 
> This sample will still work if you have Sentry SDK v1 installed, but won't work for Sentry SDK v2.
> See [Sentry V2 Sample](../sentry_v2/README.md) for the updated version.

For this sample, `sentry-sdk@1.11.0`must be installed with pip as we cannot have two versions managed with poetry at the same time. To include, run:

    poetry install
    poetry run pip install sentry-sdk==1.11.0

To run, first see [README.md](../README.md) for prerequisites. Set `SENTRY_DSN` environment variable to the Sentry DSN.
Then, run the following from this directory to start the worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The workflow should complete with the hello result. If you alter the workflow or the activity to raise an
`ApplicationError` instead, it should appear in Sentry.