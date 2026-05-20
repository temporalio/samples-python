import uuid

import pytest
from temporalio.client import Client
from temporalio.contrib.strands import StrandsPlugin
from temporalio.worker import Worker

from strands_plugin.continue_as_new.workflow import ChatInput, ChatWorkflow
from tests.strands_plugin._mock_model import patch_bedrock


async def test_continue_as_new_chat(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch_bedrock(monkeypatch, ["First reply.", "Second reply."])

    task_queue = f"strands-chat-{uuid.uuid4()}"
    plugin = StrandsPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ChatWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            ChatWorkflow.run,
            ChatInput(),
            id=f"strands-chat-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        reply1 = await handle.execute_update(ChatWorkflow.turn, "Hello")
        reply2 = await handle.execute_update(ChatWorkflow.turn, "How are you?")

        assert reply1 == "First reply."
        assert reply2 == "Second reply."

        messages = await handle.query(ChatWorkflow.messages)
        await handle.signal(ChatWorkflow.end_chat)
        await handle.result()

    # 2 user turns + 2 assistant replies
    assert len(messages) == 4
