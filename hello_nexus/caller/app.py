import asyncio
import sys
from typing import Any, Type

from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from hello_nexus.caller.workflows import (
    Echo2CallerWorkflow,
    Echo3CallerWorkflow,
    EchoCallerWorkflow,
    Hello2CallerWorkflow,
    HelloCallerWorkflow,
)

interrupt_event = asyncio.Event()


async def execute_workflow(workflow_cls: Type[Any], input: Any) -> None:
    client = await Client.connect("localhost:7233", namespace="my-caller-namespace-python")
    task_queue = "my-caller-task-queue"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[workflow_cls],
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        print("🟠 Caller worker started")
        result = await client.execute_workflow(
            workflow_cls.run,
            input,
            id="my-caller-workflow-id",
            task_queue=task_queue,
        )
        print("🟢 workflow result:", result)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m nexus.caller.app [echo|hello]")
        sys.exit(1)

    [wf_name] = sys.argv[1:]
    fn = {
        "echo": lambda: execute_workflow(EchoCallerWorkflow, "hello"),
        "echo2": lambda: execute_workflow(Echo2CallerWorkflow, "hello"),
        "echo3": lambda: execute_workflow(Echo3CallerWorkflow, "hello"),
        "hello": lambda: execute_workflow(HelloCallerWorkflow, "world"),
        "hello2": lambda: execute_workflow(Hello2CallerWorkflow, "world"),
    }[wf_name]

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(fn())
    except KeyboardInterrupt:
        interrupt_event.set()
        loop.run_until_complete(loop.shutdown_asyncgens())
