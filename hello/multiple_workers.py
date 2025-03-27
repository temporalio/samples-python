import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker


@dataclass
class ComposeGreetingInput:
    greeting: str
    name: str


@activity.defn
async def compose_greeting(input: ComposeGreetingInput) -> str:
    return f"{input.greeting}, {input.name}!"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            compose_greeting,
            ComposeGreetingInput("Hello", name),
            start_to_close_timeout=timedelta(seconds=10),
        )


@workflow.defn
class DummyWorkflow:
    """A dummy workflow that W2 will register just so it participates in task polling"""

    @workflow.run
    async def run(self) -> str:
        return "dummy"


async def run_worker(client: Client, worker_id: str, include_workflow: bool):
    """Run a worker with or without the target workflow registered"""
    # W1 gets GreetingWorkflow, W2 gets DummyWorkflow
    workflows = [GreetingWorkflow] if include_workflow else [DummyWorkflow]

    worker = Worker(
        client,
        task_queue="shared-task-queue",
        workflows=workflows,
        activities=[compose_greeting],
        workflow_runner=UnsandboxedWorkflowRunner(),
        max_cached_workflows=0,  # Disable sticky workflows
        identity=f"worker-{worker_id}",
    )

    logging.info(
        f"Starting worker {worker_id} (workflows={'GreetingWorkflow' if include_workflow else 'DummyWorkflow'})"
    )
    async with worker:
        await asyncio.Event().wait()


async def main():
    logging.basicConfig(level=logging.INFO)

    client = await Client.connect("localhost:7233")

    worker1 = asyncio.create_task(run_worker(client, "W1", include_workflow=True))
    worker2 = asyncio.create_task(run_worker(client, "W2", include_workflow=False))

    # Wait for workers to start
    await asyncio.sleep(2)

    try:
        for i in range(5):
            try:
                result = await client.execute_workflow(
                    GreetingWorkflow.run,
                    "World",
                    id=f"workflow-test-{i}",
                    task_queue="shared-task-queue",
                    task_timeout=timedelta(seconds=5),
                )
                print(f"Workflow {i} completed successfully: {result}")
            except Exception as e:
                print(f"Workflow {i} failed: {str(e)}")

            await asyncio.sleep(1)

    finally:
        # Cancel the worker tasks
        worker1.cancel()
        worker2.cancel()
        try:
            await worker1
        except asyncio.CancelledError:
            pass
        try:
            await worker2
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
