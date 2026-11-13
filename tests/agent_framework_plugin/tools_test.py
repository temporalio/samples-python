import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from agent_framework_plugin.tools.workflow import ToolsWorkflow, fetch_weather
from tests.agent_framework_plugin._fake_chat_client import (
    function_call_response,
    scripted_plugin,
    text_response,
)
from tests.agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    count_scheduled_activities,
    function_results,
    with_plugin,
)


async def test_tools(client: Client) -> None:
    plugin, factory = scripted_plugin(
        [
            function_call_response(
                "letter_counter", {"word": "strawberry", "letter": "r"}, call_id="c1"
            ),
            function_call_response(
                "fetch_weather", {"city": "San Francisco"}, call_id="c2"
            ),
            text_response("Three R's, and it is sunny in San Francisco."),
        ]
    )
    client = with_plugin(client, plugin)
    task_queue = f"agent-framework-tools-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ToolsWorkflow],
        activities=[fetch_weather],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            ToolsWorkflow.run,
            "Count the R's in strawberry and fetch the weather in San Francisco.",
            id=f"agent-framework-tools-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert result == "Three R's, and it is sunny in San Francisco."
    # Three model turns and one Activity for the wrapped tool. The pure tool
    # ran in the Workflow and left no Activity behind.
    assert await count_scheduled_activities(handle) == {
        INVOKE_MODEL: 3,
        "fetch_weather": 1,
    }
    counted, weather = function_results(factory().calls[-1]["messages"])
    assert counted == "3"
    assert "San Francisco" in weather and "sunny" in weather
