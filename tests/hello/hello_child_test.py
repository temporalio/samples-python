import uuid

from temporalio import workflow
from temporalio.worker import Worker
from temporalio.client import Client
from hello.hello_child_workflow import GreetingWorkflow, ComposeGreetingWorkflow, ComposeGreetingInput


async def test_child_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())
    async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[GreetingWorkflow, ComposeGreetingWorkflow],
    ):
        assert "Hello, World!" == await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )


@workflow.defn(name="ComposeGreetingWorkflow")
class MockedComposeGreetingWorkflow:
    @workflow.run
    async def run(self, input: ComposeGreetingInput) -> str:
        return f"{input.greeting}, {input.name} from mocked child!"


async def test_mock_child_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())
    async with Worker(
            client,
            task_queue=task_queue_name,
            workflows=[GreetingWorkflow, MockedComposeGreetingWorkflow],
    ):
        assert "Hello, World from mocked child!" == await client.execute_workflow(
            GreetingWorkflow.run,
            "World",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )
