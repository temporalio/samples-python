import uuid

import pytest
from google.adk.models.llm_request import LlmRequest
from temporalio.client import Client
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin
from temporalio.worker import Worker

from google_adk_agents.chatbot.workflows.chatbot_workflow import (
    ChatbotAgentWorkflow,
)
from tests.google_adk_agents._mock_model import patch_model, text


async def test_chatbot(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[LlmRequest] = []
    patch_model(
        monkeypatch, [text("first reply"), text("second reply")], captured=captured
    )

    task_queue = f"google-adk-agents-chatbot-{uuid.uuid4()}"
    plugin = GoogleAdkPlugin()

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ChatbotAgentWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            ChatbotAgentWorkflow.run,
            id=f"google-adk-agents-chatbot-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        first = await handle.execute_update(ChatbotAgentWorkflow.message, "Hello")
        second = await handle.execute_update(ChatbotAgentWorkflow.message, "Again")

        await handle.terminate()

    assert first == "first reply"
    assert second == "second reply"

    # The second turn reuses the same session, so its request carries the first
    # turn's history.
    turn_two_history = "\n".join(
        part.text
        for content in captured[1].contents
        for part in (content.parts or [])
        if part.text
    )
    assert "Hello" in turn_two_history
    assert "first reply" in turn_two_history
