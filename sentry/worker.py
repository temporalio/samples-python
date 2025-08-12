import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import timedelta

import sentry_sdk
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

from sentry.interceptor import SentryInterceptor


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )


async def main():
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Initialize the Sentry SDK
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
    )

    # Get repo root - 1 level deep from root


    repo_root = Path(__file__).resolve().parent.parent


    config_file = repo_root / "temporal.toml"


    
    config = ClientConfig.load_client_connect_config(config_file=str(config_file))
    config["target_host"] = "localhost:7233"
    
    # Start client
    client = await Client.connect(**config)

    # Run a worker for the workflow
    worker = Worker(
        client,
        task_queue="sentry-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        interceptors=[SentryInterceptor()],  # Use SentryInterceptor for error reporting
    )

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
