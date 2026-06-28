import json
import uuid

from temporalio.client import Client
from temporalio.contrib.google_genai.testing import GeminiTestServer, text_response
from temporalio.worker import Worker

from google_genai_plugin.structured_output.workflow import (
    Recipe,
    StructuredOutputWorkflow,
)


async def test_structured_output(client: Client) -> None:
    recipe_json = json.dumps(
        {
            "name": "Avocado Toast",
            "ingredients": ["bread", "avocado", "salt"],
            "steps": ["Toast the bread.", "Mash the avocado on top.", "Season."],
        }
    )
    server = GeminiTestServer([text_response(recipe_json)])

    config = client.config()
    config["plugins"] = [*config["plugins"], server.plugin()]
    client = Client(**config)

    task_queue = f"google-genai-structured-output-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StructuredOutputWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            StructuredOutputWorkflow.run,
            "Give me a simple recipe for avocado toast.",
            id=f"google-genai-structured-output-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert isinstance(result, Recipe)
    assert result.name == "Avocado Toast"
    assert result.ingredients == ["bread", "avocado", "salt"]
    assert len(result.steps) == 3
