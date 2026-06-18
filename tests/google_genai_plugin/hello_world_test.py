import uuid

from temporalio.client import Client
from temporalio.contrib.google_genai.testing import GeminiTestServer, text_response
from temporalio.worker import Worker

from google_genai_plugin.hello_world.workflow import HelloWorldWorkflow


async def test_hello_world(client: Client) -> None:
    server = GeminiTestServer([text_response("A haiku, for you.")])

    config = client.config()
    config["plugins"] = [*config["plugins"], server.plugin()]
    client = Client(**config)

    task_queue = f"google-genai-hello-world-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HelloWorldWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            "Write a haiku.",
            id=f"google-genai-hello-world-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "A haiku, for you."
    assert len(server.requests) == 1
