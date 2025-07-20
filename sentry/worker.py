import asyncio
import os

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.types import Event, Hint
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from sentry.activity import broken_activity, working_activity
from sentry.interceptor import SentryInterceptor
from sentry.workflow import SentryExampleWorkflow

interrupt_event = asyncio.Event()


def before_send(event: Event, hint: Hint) -> Event | None:
    # Filter out __ShutdownRequested events raised by the worker's internals
    if str(hint.get("exc_info", [None])[0].__name__) == "_ShutdownRequested":
        return None

    return event


def initialise_sentry() -> None:
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if not sentry_dsn:
        print(
            "SENTRY_DSN environment variable is not set. Sentry will not be initialized."
        )
        return

    environment = os.environ.get("ENVIRONMENT")
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        integrations=[
            AsyncioIntegration(),
        ],
        attach_stacktrace=True,
        before_send=before_send,
    )
    print(f"Sentry SDK initialized for environment: {environment!r}")


async def main():
    # Initialize the Sentry SDK
    initialise_sentry()

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="sentry-task-queue",
        workflows=[SentryExampleWorkflow],
        activities=[broken_activity, working_activity],
        interceptors=[SentryInterceptor()],  # Use SentryInterceptor for error reporting
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules(
                "sentry_sdk"
            )
        ),
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    # Note: "Addressing Concurrency Issues" section in Sentry docs recommends using
    # the AsyncioIntegration: "If you do concurrency with asyncio coroutines, make
    # sure to use the AsyncioIntegration which will clone the correct scope in your Tasks"
    # See https://docs.sentry.io/platforms/python/troubleshooting/
    #
    # However, this captures all unhandled exceptions in the event loop.
    # So handle shutdown gracefully to avoid CancelledError and KeyboardInterrupt
    # exceptions being captured as errors. Sentry also captures the worker's
    # _ShutdownRequested exception, which is probably not useful. We've filtered this
    # out in Sentry's before_send function.
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
