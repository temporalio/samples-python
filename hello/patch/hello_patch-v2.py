import asyncio
import logging
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

@workflow.defn
class PatchedWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        if workflow.patched('my-patch-v2'):
            print(f"Running new version of workflow")
            workflow.logger.info("Running new v1 workflow with parameter %s" % name)
            greeting = await workflow.execute_activity(
                compose_greeting,
                ComposeGreetingInput("Hello-v2", name),
                start_to_close_timeout=timedelta(seconds=70),
            )
            await asyncio.sleep(60)
            return greeting
        else:
            print(f"Running old version of workflow")
            workflow.logger.info("Running original workflow with parameter %s" % name)
            greeting = await workflow.execute_activity(
                compose_greeting,
                ComposeGreetingInput("Hello", name),
                start_to_close_timeout=timedelta(seconds=70),
            )
            await asyncio.sleep(60)
            return greeting


async def main():
    # Uncomment the line below to see logging
    # logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect("localhost:7233")

    # Run a worker for the workflow
    async with Worker(
        client,
        task_queue="hello-patched-task-queue",
        workflows=[PatchedWorkflow],
        activities=[compose_greeting],
    ):

        # While the worker is running, use the client to run the workflow and
        # print out its result. Check if the workflow is already running and if so
        # wait for it to complete. Note, in many production setups, the client
        # would be in a completely separate process from the worker.
        try:
            result = await client.execute_workflow(
                PatchedWorkflow.run,
                "World",
                id="hello-patched-workflow-id",
                task_queue="hello-patched-task-queue",
            )
            print(f"Result: {result}")
        except exceptions.WorkflowAlreadyStartedError:
            print(f"Workflow already running")
            workflow_result = await client.get_workflow_handle(
                "hello-patched-workflow-id"
            ).result()
            print(f"Successful workflow result: {workflow_result}")

if __name__ == "__main__":
    asyncio.run(main())
