import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, exceptions, workflow
from temporalio.client import Client
from temporalio.worker import Worker


# While we could use multiple parameters in the activity, Temporal strongly
# encourages using a single dataclass instead which can have fields added to it
# in a backwards-compatible way.
@dataclass
class ComposeGreetingInput:
    greeting = "Hello"
    name: str


# Basic activity that logs and does string concatenation
@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"


# Depending on version argument passed in, will execute a different workflow.
# The v1 workflow shows the original workflow with a single activity that
# outputs "Hello, World". If we wanted to change this workflow without breaking
# already running workflows, we can use patched. The v2 workflow shows how to
# use patched to continue to output "Hello, World" for already running workflows
# and output "Hello, Universe" for newly started workflows. The timer (sleep) exists
# to allow experimentation, around how changes affect running workflows.
@workflow.defn
class PatchWorkflow:
    @workflow.run
    async def run(self, version: str) -> str:
        greeting = ""
        if version == "v1":
            print(f"Running workflow version {version}")
            workflow.logger.info("Running workflow version {version}")
            greeting = await workflow.execute_activity(
                compose_greeting,
                ComposeGreetingInput("World"),
                start_to_close_timeout=timedelta(seconds=70),
            )

            await asyncio.sleep(60)
        elif version == "v2":
            print(f"Running workflow version {version}")
            workflow.logger.info("Running workflow version {version}")
            if workflow.patched("my-patch-v2"):
                greeting = await workflow.execute_activity(
                    compose_greeting,
                    ComposeGreetingInput("Universe"),
                    start_to_close_timeout=timedelta(seconds=70),
                )

                await asyncio.sleep(60)
            else:
                greeting = await workflow.execute_activity(
                    compose_greeting,
                    ComposeGreetingInput("World"),
                    start_to_close_timeout=timedelta(seconds=70),
                )

                await asyncio.sleep(60)
        return greeting


async def main():
    # Check arguments and ensure either v1 or v2 is passed in
    if len(sys.argv) > 2:
        print(f"Incorrect arguments: {sys.argv[0]} v1 or {sys.argv[0]} v2")
        exit()
    if len(sys.argv) <= 1:
        print(f"Incorrect arguments: {sys.argv[0]} v1 or {sys.argv[0]} v2")
        exit()
    if sys.argv[1] != "v1" and sys.argv[1] != "v2":
        print(f"Incorrect arguments: {sys.argv[0]} v1 or {sys.argv[0]} v2")
        exit()

    version = sys.argv[1]

    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-patch-task-queue",
        workflows=[PatchWorkflow],
        activities=[compose_greeting],
    ):
        # While the worker is running, use the client to run the workflow and
        # print out its result. Check if the workflow is already running and if so
        # wait for the existing run to complete. Note, in many production setups,
        # the client would be in a completely separate process from the worker.
        try:
            result = await client.execute_workflow(
                PatchWorkflow.run,
                version,
                id="hello-patch-workflow-id",
                task_queue="hello-patch-task-queue",
            )
            print(f"Result: {result}")
        except exceptions.WorkflowAlreadyStartedError:
            print(f"Workflow already running")
            result = await client.get_workflow_handle(
                "hello-patch-workflow-id"
            ).result()
            print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
