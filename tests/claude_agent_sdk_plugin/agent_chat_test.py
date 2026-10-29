import json
import uuid

import pytest
from temporalio.api.enums.v1 import EventType
from temporalio.claude_agent_sdk import ClaudeAgentSDKPlugin
from temporalio.client import Client, WorkflowContinuedAsNewError
from temporalio.worker import Replayer, Worker

from claude_agent_sdk_plugin.agent_chat.workflow import ChatInput, ChatWorkflow
from claude_agent_sdk_plugin.offline import prompt_of, scripted_api

ANSWERS = {
    "Ada": "Nice to meet you, Ada.",
    "Lovelace": "Ada Lovelace, noted.",
    "my name": "Your name is Ada Lovelace.",
}


async def test_chat_resumes_claude_session_after_continue_as_new(
    client: Client,
) -> None:
    task_queue = f"claude-agent-sdk-agent-chat-{uuid.uuid4()}"
    workflow_id = f"claude-agent-sdk-agent-chat-{uuid.uuid4()}"
    with scripted_api(ANSWERS) as api:
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatWorkflow],
            plugins=[ClaudeAgentSDKPlugin()],
        ):
            first = await client.start_workflow(
                ChatWorkflow.run,
                ChatInput(turns_per_run=2),
                id=workflow_id,
                task_queue=task_queue,
            )
            assert (
                await first.execute_update(ChatWorkflow.send_message, "I'm Ada.")
                == "Nice to meet you, Ada."
            )
            assert (
                await first.execute_update(
                    ChatWorkflow.send_message, "My surname is Lovelace."
                )
                == "Ada Lovelace, noted."
            )
            with pytest.raises(WorkflowContinuedAsNewError):
                await first.result(follow_runs=False)

            second = client.get_workflow_handle(workflow_id)
            assert (
                await second.execute_update(
                    ChatWorkflow.send_message, "What is my name?"
                )
                == "Your name is Ada Lovelace."
            )
            await second.signal(ChatWorkflow.end_conversation)
            await second.result()

    after_resume = next(r for r in api.requests if "What is my name?" in prompt_of(r))
    conversation = json.dumps(after_resume["messages"])
    assert "I'm Ada." in conversation
    assert "Ada Lovelace, noted." in conversation

    first_run = client.get_workflow_handle(workflow_id, run_id=first.result_run_id)
    first_history = await first_run.fetch_history()
    continued = first_history.events[-1]
    assert (
        continued.event_type == EventType.EVENT_TYPE_WORKFLOW_EXECUTION_CONTINUED_AS_NEW
    )
    [carried] = await client.data_converter.decode(
        continued.workflow_execution_continued_as_new_event_attributes.input.payloads,
        [ChatInput],
    )
    assert carried.session_id
    assert carried.turns_per_run == 2

    replayer = Replayer(workflows=[ChatWorkflow], plugins=[ClaudeAgentSDKPlugin()])
    await replayer.replay_workflow(first_history)
    await replayer.replay_workflow(await second.fetch_history())
