import uuid

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from fast_api.run_worker import SayHello, say_hello


async def test_execute_workflow(client: Client):
    task_queue_name = str(uuid.uuid4())

    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[SayHello],
        activities=[say_hello],
    ):
        assert "Hello, World!" == await client.execute_workflow(
            SayHello.run,
            "World",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )


@activity.defn(name="say_hello")
async def say_hello_mocked(name: str) -> str:
    return f"Hello, {name} from mocked activity!"


async def test_mock_activity(client: Client):
    task_queue_name = str(uuid.uuid4())
    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[SayHello],
        activities=[say_hello_mocked],
    ):
        assert "Hello, World from mocked activity!" == await client.execute_workflow(
            SayHello.run,
            "World",
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
        )
