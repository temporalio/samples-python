import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

with workflow.unsafe.imports_passed_through():
    import sentry_sdk

    from sentry.interceptor import SentryInterceptor
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration


logger = logging.getLogger(__name__)


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    raise Exception("Activity failed!")


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )


async def main():
    # Uncomment the line below to see logging
    logging.basicConfig(level=logging.INFO)

    # Initialize the Sentry SDK
    if sentry_dsn := os.environ.get("SENTRY_DSN"):
        environment = os.environ.get("ENVIRONMENT")
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            integrations=[
                AsyncioIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.WARNING,
                ),
            ],
            attach_stacktrace=True,
        )
        logger.info(f"Sentry SDK initialized for environment: {environment!r}")
    else:
        logger.warning(
            "SENTRY_DSN environment variable is not set. Sentry will not be initialized."
        )

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    worker = Worker(
        client,
        task_queue="sentry-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        interceptors=[SentryInterceptor()],  # Use SentryInterceptor for error reporting
        # workflow_runner=SandboxedWorkflowRunner(
        #     restrictions=SandboxRestrictions.default.with_passthrough_modules(
        #         "sentry_sdk"
        #     )
        # ),
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
