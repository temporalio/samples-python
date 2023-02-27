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


async def timer(time: int) -> int:
    asyncio.sleep(time)


# Basic workflow that execute a activity and fires a timer. Demonstrates how to version a workflow using patched.
# Steps
# 1) First run the workflow
# 2) Ctrl-C and interrupt workflow
# 3) Comment the current async run function and comment out the async run function with patch (this simulates patching a running workflow)
# 4) Re-run the workflow, it will detect a workflow is running and pickup the execution following the old code path
# 5) Re-run the workflow again, since a workflow isn't running it will pickup execution following the new code path


@workflow.defn
class PatchedWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info("Running workflow with parameter %s" % name)
        greeting = await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=60),
        )
        await asyncio.sleep(120)
        return greeting


#    async def run(self, name: str) -> str:
#        if workflow.patched('my-patch-v1'):
#            print(f"Running new version of workflow")
#            workflow.logger.info("Running new v1 workflow with parameter %s" % name)
#            greeting = await workflow.execute_activity(
#                compose_greeting,
#                ComposeGreetingInput("Hello-v1", name),
#                start_to_close_timeout=timedelta(seconds=60),
#            )
#            await asyncio.sleep(120)
#            return greeting
#        else:
#            print(f"Running old version of workflow")
#            workflow.logger.info("Running original workflow with parameter %s" % name)
#            greeting = await workflow.execute_activity(
#                compose_greeting,
#                ComposeGreetingInput("Hello", name),
#                start_to_close_timeout=timedelta(seconds=60),
#            )
#            await asyncio.sleep(120)
#            return greeting


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

    # while(True):
    #     await asyncio.sleep(30)
    #     print(f"Working waiting on tasks...")


if __name__ == "__main__":
    asyncio.run(main())
