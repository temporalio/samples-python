import uuid

from temporalio.client import Client
from temporalio.contrib.google_genai.testing import GeminiTestServer, text_response
from temporalio.worker import Worker

from google_genai_plugin.chat.workflow import ChatWorkflow


async def test_chat(client: Client) -> None:
    server = GeminiTestServer(
        [
            text_response("Got it — your favorite color is teal."),
            text_response("Your favorite color is teal."),
        ]
    )

    config = client.config()
    config["plugins"] = [*config["plugins"], server.plugin()]
    client = Client(**config)

    task_queue = f"google-genai-chat-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ChatWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            ChatWorkflow.run,
            [
                "My favorite color is teal. Remember that.",
                "What is my favorite color?",
            ],
            id=f"google-genai-chat-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == [
        "Got it — your favorite color is teal.",
        "Your favorite color is teal.",
    ]
    assert len(server.requests) == 2
