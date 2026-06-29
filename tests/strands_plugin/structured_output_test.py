import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.structured_output.workflow import (
    PersonInfo,
    StructuredOutputWorkflow,
)
from tests.strands_plugin._mock_model import patch_bedrock


async def test_structured_output(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_bedrock(
        monkeypatch,
        [
            {
                "name": "PersonInfo",
                "input": {
                    "name": "John Smith",
                    "age": 30,
                    "occupation": "software engineer",
                },
            },
        ],
    )

    task_queue = f"strands-structured-output-{uuid.uuid4()}"
    plugin = StrandsPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[StructuredOutputWorkflow],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            StructuredOutputWorkflow.run,
            "John Smith is a 30 year-old software engineer.",
            id=f"strands-structured-output-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == PersonInfo(
        name="John Smith", age=30, occupation="software engineer"
    )
