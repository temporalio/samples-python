import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from util import get_temporal_config_path


# While we could use multiple parameters in the activity, Temporal strongly
# encourages using a single dataclass instead which can have fields added to it
# in a backwards-compatible way.
@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


# Basic activity that logs and does string concatenation
@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"


# A workflow which just runs an activity
@workflow.defn
class JustActivity:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running just activity workflow with parameter %s" % name)
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )


# A workflow which just runs a timer
@workflow.defn
class JustTimer:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running just timer workflow with parameter %s" % name)
        await asyncio.sleep(0.1)
        return "Slept"


# A workflow which runs a timer then an activity
@workflow.defn
class TimerThenActivity:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info(
            "Running timer then activity workflow with parameter %s" % name
        )
        await asyncio.sleep(0.1)
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )


interrupt_event = asyncio.Event()


async def main():
    # Uncomment the line below to see logging
    logging.basicConfig(level=logging.INFO)

    # Start client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="replay-sample",
        workflows=[JustActivity, JustTimer, TimerThenActivity],
        activities=[compose_greeting],
    ):
        # Wait until interrupted
        print("Worker started, ctrl+c to exit")
        await interrupt_event.wait()
        print("Shutting down")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
