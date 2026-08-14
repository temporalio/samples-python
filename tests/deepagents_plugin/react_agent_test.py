import uuid

from langchain_core.messages import AIMessage
from temporalio.client import Client
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.react_agent.workflow import ReactAgent, get_weather
from tests.deepagents_plugin.helpers import INVOKE_TOOL, count_scheduled_activities


async def test_react_agent(client: Client) -> None:
    # Script the model through the tool loop: call get_weather, then web_search,
    # then answer. The tools run for real (get_weather as an activity, web_search
    # wrapped via tool_as_activity); only the model turns are scripted.
    call_weather = AIMessage(
        content="",
        tool_calls=[{"name": "get_weather", "args": {"city": "Paris"}, "id": "c1"}],
    )
    call_search = AIMessage(
        content="",
        tool_calls=[{"name": "web_search", "args": {"query": "Temporal"}, "id": "c2"}],
    )
    final = AIMessage(content="It is sunny in Paris and Temporal keeps code durable.")
    plugin = DeepAgentsPlugin(
        model_provider=mock_model_provider([call_weather, call_search, final]),
    )
    task_queue = f"deepagents-react-agent-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ReactAgent],
        activities=[get_weather],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            ReactAgent.run,
            "What's the weather in Paris, and what is Temporal?",
            id=f"deepagents-react-agent-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert "durable" in result
    # Both tool seams really crossed the activity boundary: get_weather ran as
    # the user's own activity (activity_as_tool) and web_search ran through the
    # plugin's invoke_tool activity (tool_as_activity).
    counts = await count_scheduled_activities(handle)
    assert counts["get_weather"] == 1, counts
    assert counts[INVOKE_TOOL] == 1, counts
