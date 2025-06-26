import asyncio
import uuid
from typing import Optional

from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from hello_nexus.basic.caller.workflows import CallerWorkflow
from hello_nexus.basic.service import MyOutput

NAMESPACE = "hello-nexus-basic-caller-namespace"
TASK_QUEUE = "hello-nexus-basic-caller-task-queue"


async def execute_caller_workflow(
    client: Optional[Client] = None,
) -> tuple[MyOutput, MyOutput]:
    client = client or await Client.connect(
        "localhost:7233",
        namespace=NAMESPACE,
    )

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CallerWorkflow],
        # TODO(dan): isinstance(op, nexusrpc.contract.Operation) is failing under the
        # sandbox in temporalio/worker/_interceptor.py
        workflow_runner=UnsandboxedWorkflowRunner(),
    ):
        return await client.execute_workflow(
            CallerWorkflow.run,
            arg="world",
            id=str(uuid.uuid4()),
            task_queue=TASK_QUEUE,
        )


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(execute_caller_workflow())
        for output in results:
            print(output.message)
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
