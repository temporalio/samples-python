import uuid

from temporalio.client import Client
from temporalio.worker import Worker

from agent_framework_plugin.multi_agent.workflow import MultiAgentWorkflow
from tests.agent_framework_plugin._fake_chat_client import (
    function_call_response,
    scripted_plugin,
    text_response,
)
from tests.agent_framework_plugin.helpers import (
    INVOKE_MODEL,
    INVOKE_MODEL_STREAMING,
    activity_summaries,
    count_scheduled_activities,
    with_plugin,
)

FACTS = "Fact one. Fact two. Fact three."
PARAGRAPH = "Durable execution keeps going where a process would have stopped."


async def test_multi_agent(client: Client) -> None:
    # All three agents share the "gpt-4o-mini" client, so one script serves
    # them in call order: coordinator, researcher, coordinator, writer, coordinator.
    plugin, factory = scripted_plugin(
        [
            function_call_response(
                "researcher", {"task": "facts about durable execution"}, call_id="c1"
            ),
            text_response(FACTS),
            function_call_response("writer", {"task": FACTS}, call_id="c2"),
            text_response(PARAGRAPH),
            text_response(f"Here it is: {PARAGRAPH}"),
        ]
    )
    client = with_plugin(client, plugin)
    task_queue = f"agent-framework-multi-agent-{uuid.uuid4()}"

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[MultiAgentWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            MultiAgentWorkflow.run,
            "durable execution",
            id=f"agent-framework-multi-agent-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        result = await handle.result()

    assert result == f"Here it is: {PARAGRAPH}"
    # Five model calls in one Workflow: three by the coordinator and one per
    # sub-agent. Agent.as_tool() runs the sub-agent streaming, so those two
    # are the streaming Activity.
    assert await count_scheduled_activities(handle) == {
        INVOKE_MODEL: 3,
        INVOKE_MODEL_STREAMING: 2,
    }
    assert await activity_summaries(handle) == [
        "coordinator",
        "researcher",
        "coordinator",
        "writer",
        "coordinator",
    ]
    # The sub-agents got the coordinator's tasks with their own instructions.
    calls = factory().calls
    assert calls[1]["messages"][-1].text == "facts about durable execution"
    assert calls[1]["options"]["instructions"] == (
        "List three short facts about the topic you are given."
    )
    assert calls[3]["messages"][-1].text == FACTS
