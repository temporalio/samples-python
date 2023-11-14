import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from custom_converter.shared import (
    GreetingInput,
    GreetingOutput,
    greeting_data_converter,
)
from custom_converter.workflow import GreetingWorkflow


async def test_workflow_with_custom_converter(client: Client):
    # Replace data converter in client
    new_config = client.config()
    new_config["data_converter"] = greeting_data_converter
    client = Client(**new_config)
    task_queue = f"tq-{uuid.uuid4()}"
    async with Worker(client, task_queue=task_queue, workflows=[GreetingWorkflow]):
        result = await client.execute_workflow(
            GreetingWorkflow.run,
            GreetingInput("Temporal"),
            id=f"wf-{uuid.uuid4()}",
            task_queue=task_queue,
        )
    assert isinstance(result, GreetingOutput)
    assert result.result == "Hello, Temporal"
