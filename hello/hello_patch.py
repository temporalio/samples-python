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
    greeting: str
    name: str


# Basic activity that logs and does string concatenation
@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"


# MyWorkflowDeployedFirst workflow is example of first version of workflow
@workflow.defn
class MyWorkflowDeployedFirst:
    @workflow.run
    async def run(self, name: str) -> str:
        print(f"Running MyWorkflowDeployedFirst workflow with parameter %s" % name)
        workflow.logger.info(
            "Running MyWorkflowDeployedFirst workflow with parameter %s" % name
        )
        greeting = await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=70),
        )
        return greeting


# MyWorkflowPatched workflow is example of using patch to change the workflow for
# newly started workflows without changing the behavior of existing workflows.
@workflow.defn
class MyWorkflowPatched:
    @workflow.run
    async def run(self, name: str) -> str:
        print(f"Running MyWorkflowPatched workflow with parameter %s" % name)
        workflow.logger.info(
            "Running MyWorkflowPatched workflow with parameter %s" % name
        )
        if workflow.patched("my-patch-v2"):
            greeting = await workflow.execute_activity(
                compose_greeting,
                ComposeGreetingInput("Goodbye", name),
                start_to_close_timeout=timedelta(seconds=70),
            )

            print(f"Fire a timer and sleep for 10 seconds")
            await asyncio.sleep(10)
            return greeting
        else:
            greeting = await workflow.execute_activity(
                compose_greeting,
                ComposeGreetingInput("Hello", name),
                start_to_close_timeout=timedelta(seconds=70),
            )
            return greeting


# MyWorkflowPatchDeprecated workflow is example for after no older workflows are
# running and we want to deprecate the patch and just use the new version.
@workflow.defn
class MyWorkflowPatchDeprecated:
    @workflow.run
    async def run(self, name: str) -> str:
        print(f"Running MyWorkflowPatchDeprecated workflow with parameter %s" % name)
        workflow.logger.info(
            "Running MyWorkflowPatchDeprecated workflow with parameter %s" % name
        )
        workflow.deprecate_patch("my-patch-v2")
        greeting = await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Goodbye", name),
            start_to_close_timeout=timedelta(seconds=70),
        )

        print(f"Fire a timer and sleep for 10 seconds")
        await asyncio.sleep(10)
        return greeting


async def main():
    # Check arguments and ensure either v1, v2 or v3 is passed in as argument
    if len(sys.argv) > 2:
        print(
            f"Incorrect arguments: {sys.argv[0]} v1 or {sys.argv[0]} v2 or {sys.argv[0]} v3"
        )
        exit()
    if len(sys.argv) <= 1:
        print(
            f"Incorrect arguments: {sys.argv[0]} v1 or {sys.argv[0]} v2 or {sys.argv[0]} v3"
        )
        exit()
    if sys.argv[1] != "v1" and sys.argv[1] != "v2" and sys.argv[1] != "v3":
        print(
            f"Incorrect arguments: {sys.argv[0]} v1 or {sys.argv[0]} v2 or {sys.argv[0]} v3"
        )
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
        workflows=[
            MyWorkflowDeployedFirst,
            MyWorkflowPatched,
            MyWorkflowPatchDeprecated,
        ],
        activities=[compose_greeting],
    ):
        # While the worker is running, use the client to run the workflow and
        # print out its result. A workflow will be chosen based on argument passed in.
        # Check if the workflow is already running and if so wait for the
        # existing run to complete. Note, in many production setups,
        # the client would be in a completely separate process from the worker.

        if version == "v1":
            try:
                result = await client.execute_workflow(
                    MyWorkflowDeployedFirst.run,
                    "World",
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
        elif version == "v2":
            try:
                result = await client.execute_workflow(
                    MyWorkflowPatched.run,
                    "World",
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
        elif version == "v3":
            try:
                result = await client.execute_workflow(
                    MyWorkflowPatchDeprecated.run,
                    "World",
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
        else:
            print(
                f"Incorrect arguments: {sys.argv[0]} v1 or {sys.argv[0]} v2 or {sys.argv[0]} v3"
            )
            exit()


if __name__ == "__main__":
    asyncio.run(main())
