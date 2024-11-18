# Sentry Sample

This sample shows how to configure [Sentry](https://sentry.io) SDK (version 2) to intercept and capture errors from the Temporal SDK
for workflows and activities. The integration adds some useful context to the errors, such as the activity type, task queue, etc.

### Further details

This is a small modification of the original example Sentry integration in this repo based on SDK v1. The integration
didn't work properly with Sentry SDK v2 due to some internal changes in the Sentry SDK that broke the worker sandbox. 
Additionally, the v1 SDK has been deprecated and is only receiving security patches and will reach EOL some time in the future.

If you still need to use Sentry SDK v1, check the original example at this [commit](https://github.com/temporalio/samples-python/tree/7b3944926c3743bc0dcb3b781d8cc64e0330bac4/sentry). 

Sentry's `Hub` object is now deprecated in the v2 SDK in favour of scopes. See [Activating Current Hub Clone](https://docs.sentry.io/platforms/python/migration/1.x-to-2.x#activating-current-hub-clone)
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

## Screenshot

The screenshot below shows the extra tags and context included in the 
Sentry error from the exception thrown in the activity.

![Sentry screenshot](images/sentry.jpeg)