import uuid

from temporalio.api.enums.v1 import EventType
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.hooks.run_worker import OFFLINE_ANSWERS
from claude_agent_sdk_plugin.hooks.workflow import HooksWorkflow, audit_command
from claude_agent_sdk_plugin.offline import scripted_api


async def test_hooks(client: Client) -> None:
    task_queue = f"claude-agent-sdk-hooks-{uuid.uuid4()}"

    with scripted_api(OFFLINE_ANSWERS) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[HooksWorkflow],
            activities=[audit_command],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            handle = await client.start_workflow(
                HooksWorkflow.run,
                "Run echo hello, then delete hello.txt.",
                id=f"claude-agent-sdk-hooks-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            result = await handle.result()

    assert result == "The command that deletes hello.txt was blocked."
    denied = next(
        block
        for message in api.requests[-1]["messages"]
        if message["role"] == "user" and isinstance(message["content"], list)
        for block in message["content"]
        if block.get("tool_use_id") == "toolu_delete"
    )
    assert denied["is_error"]
    assert "Commands that delete files are blocked" in str(denied["content"])

    history = await handle.fetch_history()
    audited = [
        event.activity_task_scheduled_event_attributes.activity_type.name
        for event in history.events
        if event.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED
    ]
    assert audited.count("audit_command") == 1

    await Replayer(
        workflows=[HooksWorkflow], plugins=[ClaudeAgentSDKPlugin()]
    ).replay_workflow(history)
