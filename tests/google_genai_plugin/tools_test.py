import uuid

from temporalio.client import Client
from temporalio.contrib.google_genai.testing import (
    GeminiTestServer,
    function_call_response,
    text_response,
)
from temporalio.worker import Worker

from google_genai_plugin.tools.workflow import ToolsWorkflow, get_weather


async def test_tools(client: Client) -> None:
    server = GeminiTestServer(
        [
            function_call_response("get_weather", {"city": "Tokyo"}),
            function_call_response(
                "recommend_activity", {"weather": "It's 72F and sunny in Tokyo."}
            ),
            text_response("It's sunny in Tokyo — go for a hike!"),
        ]
    )

    config = client.config()
    config["plugins"] = [*config["plugins"], server.plugin()]
    client = Client(**config)

    task_queue = f"google-genai-tools-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ToolsWorkflow],
        activities=[get_weather],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            ToolsWorkflow.run,
            "What's the weather in Tokyo, and what should I do there?",
            id=f"google-genai-tools-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "It's sunny in Tokyo — go for a hike!"
    # One model turn per response: two tool calls and a final text answer.
    assert len(server.requests) == 3
