import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk_agents.tools.activities.weather_activity import get_weather
from google_adk_agents.tools.workflows.weather_workflow import WeatherAgentWorkflow
from tests.google_adk_agents._mock_model import patch_model, text, tool_call


async def test_tools(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    patch_model(
        monkeypatch,
        [
            tool_call("get_weather", {"city": "New York"}),
            text("It is warm and sunny."),
        ],
    )

    task_queue = f"google-adk-agents-tools-{uuid.uuid4()}"
    plugin = GoogleAdkPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[WeatherAgentWorkflow],
        activities=[get_weather],
        max_cached_workflows=0,
    ):
        result = await client.execute_workflow(
            WeatherAgentWorkflow.run,
            "Weather in New York?",
            id=f"google-adk-agents-tools-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert result == "It is warm and sunny."
