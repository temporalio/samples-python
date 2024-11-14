# Sentry V2 Sample

This sample shows how to configure [Sentry](https://sentry.io) SDK V2 to intercept and capture errors from the Temporal SDK.

### Further details

This is a small modification of the original example [Sentry (v1)](../sentry_v1) interceptor which doesn't work properly 
with SDK V2, due to sandbox issues.

Sentry's `Hub` object is now deprecated in the V2 SDK in favour of scopes. See [Activating Current Hub Clone](https://docs.sentry.io/platforms/python/migration/1.x-to-2.x#activating-current-hub-clone)
for more details. The changes are simple, just replace `with Hub(Hub.current):` with `with isolation_scope() as scope:`.
These changes resolve the sandbox issues.

## Running the Sample

For this sample, the optional `sentry` dependency group must be included. To include, run:

    poetry install --with sentry

To run, first see [README.md](../README.md) for prerequisites. Set `SENTRY_DSN` environment variable to the Sentry DSN.
Then, run the following from this directory to start the worker:

    poetry run python worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    poetry run python starter.py

The workflow should complete with the hello result. If you alter the workflow or the activity to raise an
`ApplicationError` instead, it should appear in Sentry.