import asyncio
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import SharedStateManager, Worker

from util import get_temporal_config_path


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
def compose_greeting(input: ComposeGreetingInput) -> str:
    # We'll wait for 3 seconds, heartbeating in between (like all long-running
    # activities should do), then return the greeting
    for _ in range(0, 3):
        print(f"Heartbeating activity on PID {os.getpid()}")
        activity.heartbeat()
        time.sleep(1)
    return f"{input.greeting}, {input.name}!"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
            # Always set a heartbeat timeout for long-running activities
            heartbeat_timeout=timedelta(seconds=2),
        )


async def main():
    # Start client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-activity-multiprocess-task-queue",
        workflows=[GreetingWorkflow],
        activities=[compose_greeting],
        # Synchronous activities are not allowed unless we provide some kind of
        # executor. Here we are giving a process pool executor which means the
        # activity will actually run in a separate process. This same executor
        # could be passed to multiple workers if desired.
        activity_executor=ProcessPoolExecutor(5),
        # Since we are using an executor that is not a thread pool executor,
        # Temporal needs some kind of manager to share state such as
        # cancellation info and heartbeat info between the host and the
        # activity. Therefore, we must provide a shared_state_manager here. A
        # helper is provided to create it from a multiprocessing manager.
        shared_state_manager=SharedStateManager.create_from_multiprocessing(
            multiprocessing.Manager()
        ),
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id="hello-activity-multiprocess-workflow-id",
            task_queue="hello-activity-multiprocess-task-queue",
        )
        print(f"Result on PID {os.getpid()}: {result}")


if __name__ == "__main__":
    asyncio.run(main())
