import uuid

from temporalio.api.enums.v1 import EventType
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.offline import Answer, scripted_api, tool_use
from claude_agent_sdk_plugin.tools.workflow import ToolsWorkflow, fetch_weather


async def test_tools(client: Client) -> None:
    answers: dict[str, Answer] = {
        "strawberry": tool_use(
            "toolu_count", "mcp__demo__count_letter", word="strawberry", letter="r"
        ),
        "tool_result:toolu_count": tool_use(
            "toolu_weather", "mcp__demo__get_weather", city="Paris"
        ),
        "tool_result:toolu_weather": "3 r's in strawberry. 21 C and sunny in Paris.",
    }
    task_queue = f"claude-agent-sdk-tools-{uuid.uuid4()}"

    with scripted_api(answers) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ToolsWorkflow],
            activities=[fetch_weather],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                ToolsWorkflow.run,
                "Count the r's in strawberry, then get the weather in Paris.",
                id=f"claude-agent-sdk-tools-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            result = await handle.result()

    assert result == "3 r's in strawberry. 21 C and sunny in Paris."
    assert api.asked == [
        "strawberry",
        "tool_result:toolu_count",
        "tool_result:toolu_weather",
    ]
    tool_results = [
        block["content"][0]["text"]
        for message in api.requests[-1]["messages"]
        if message["role"] == "user" and isinstance(message["content"], list)
        for block in message["content"]
        if block.get("type") == "tool_result"
    ]
    assert tool_results == ["3", "It is 21 C and sunny in Paris."]
    assert [t["name"] for t in api.requests[0]["tools"]] == [
        "mcp__demo__count_letter",
        "mcp__demo__get_weather",
    ]

    history = await handle.fetch_history()
    scheduled = [
        event.activity_task_scheduled_event_attributes.activity_type.name
        for event in history.events
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED
    ]
    assert scheduled.count("fetch_weather") == 1
    assert "count_letter" not in scheduled

    await Replayer(
        workflows=[ToolsWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(history)
