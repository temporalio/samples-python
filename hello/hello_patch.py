import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
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
def compose_greeting(input: ComposeGreetingInput) -> str:
    activity.logger.info("Running activity with parameter %s" % input)
    return f"{input.greeting}, {input.name}!"


# V1 of patch-workflow
@workflow.defn(name="patch-workflow")
class MyWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running patch-workflow with parameter %s" % name)
        greeting = await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=70),
        )
        return greeting


# V2 of patch-workflow using patched where we have changed newly started
# workflow behavior without changing the behavior of currently running workflows
@workflow.defn(name="patch-workflow")
class MyWorkflowPatched:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running patch-workflow with parameter %s" % name)
        if workflow.patched("my-patch-v2"):
            greeting = await workflow.execute_activity(
                compose_greeting,
                ComposeGreetingInput("Goodbye", name),
                start_to_close_timeout=timedelta(seconds=70),
            )

            await asyncio.sleep(10)
            return greeting
        else:
            greeting = await workflow.execute_activity(
                compose_greeting,
                ComposeGreetingInput("Hello", name),
                start_to_close_timeout=timedelta(seconds=70),
            )
            return greeting


# V3 of patch-workflow using deprecate_patch where all the old V1 workflows
# have completed, we no longer need to preserve V1 and now just have V2
@workflow.defn(name="patch-worklow")
class MyWorkflowPatchDeprecated:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running patch-workflow with parameter %s" % name)
        workflow.deprecate_patch("my-patch-v2")
        greeting = await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Goodbye", name),
            start_to_close_timeout=timedelta(seconds=70),
        )

        await asyncio.sleep(10)
        return greeting


async def main():
    # Check Args
    if len(sys.argv) > 2:
        print(f"Incorrect arguments: {sys.argv[0]} v1|v2|v3")
        exit()
    if len(sys.argv) <= 1:
        print(f"Incorrect arguments: {sys.argv[0]} v1|v2|v3v3")
        exit()
    if sys.argv[1] != "v1" and sys.argv[1] != "v2" and sys.argv[1] != "v3":
        print(f"Incorrect arguments: {sys.argv[0]} v1|v2|v3")
        exit()

    version = sys.argv[1]

    # Uncomment the lines below to see logging output
    # import logging
    # logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect("localhost:7233")

    # Set workflow_class to the proper class based on version
    workflow_class = ""
    if version == "v1":
        workflow_class = MyWorkflow  # type: ignore
    elif version == "v2":
        workflow_class = MyWorkflowPatched  # type: ignore
    elif version == "v3":
        workflow_class = MyWorkflowPatchDeprecated  # type: ignore
    else:
        print(f"Incorrect arguments: {sys.argv[0]} v1|v2|v3")
        exit()

    # While the worker is running, use the client to run the workflow and
    # print out its result. Check if the workflow is already running and
    # if so wait for the existing run to complete. Note, in many production setups,
    # the client would be in a completely separate process from the worker.
    async with Worker(
        client,
        task_queue="hello-patch-task-queue",
        workflows=[workflow_class],  # type: ignore
        activities=[compose_greeting],
        activity_executor=ThreadPoolExecutor(5),
    ):
        try:
            result = await client.execute_workflow(
                workflow_class.run,  # type: ignore
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


if __name__ == "__main__":
    asyncio.run(main())
