import asyncio
import sys
import uuid
from unittest.mock import patch

import pytest
from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.human_in_the_loop.workflow import (
    ChatbotWorkflow,
    make_chatbot_graph,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="langgraph.types.interrupt() requires Python >= 3.11 for async context propagation",
)


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _EchoModel:
    """Stand-in for a chat model that echoes the prompt back as its response."""

    async def ainvoke(self, prompt: str) -> _FakeMessage:
        return _FakeMessage(prompt)


def _fake_init_chat_model(*args: object, **kwargs: object) -> _EchoModel:
    return _EchoModel()


_patch_llm = lambda: patch(
    "langgraph_plugin.graph_api.human_in_the_loop.workflow.init_chat_model",
    _fake_init_chat_model,
)


async def test_human_in_the_loop_approve(client: Client) -> None:
    task_queue = f"hitl-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(graphs={"chatbot": make_chatbot_graph()})

    with _patch_llm():
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatbotWorkflow],
            plugins=[plugin],
        ):
            handle = await client.start_workflow(
                ChatbotWorkflow.run,
                "test message",
                id=f"hitl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Poll for draft to be ready
            draft = None
            for _ in range(40):
                await asyncio.sleep(0.25)
                draft = await handle.query(ChatbotWorkflow.get_draft)
                if draft is not None:
                    break
            assert draft is not None
            assert "test message" in draft

            # Approve
            await handle.signal(ChatbotWorkflow.provide_feedback, "approve")
            result = await handle.result()

    assert result == draft  # approved draft returned as-is


async def test_human_in_the_loop_revise(client: Client) -> None:
    task_queue = f"hitl-revise-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(graphs={"chatbot": make_chatbot_graph()})

    with _patch_llm():
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatbotWorkflow],
            plugins=[plugin],
        ):
            handle = await client.start_workflow(
                ChatbotWorkflow.run,
                "test message",
                id=f"hitl-revise-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Poll for draft
            draft = None
            for _ in range(40):
                await asyncio.sleep(0.25)
                draft = await handle.query(ChatbotWorkflow.get_draft)
                if draft is not None:
                    break
            assert draft is not None

            # Send revision feedback
            await handle.signal(
                ChatbotWorkflow.provide_feedback, "please be more concise"
            )
            result = await handle.result()

    # The revision node feeds the draft and feedback into the LLM; the echo
    # stand-in returns the revision prompt, which contains both.
    assert "please be more concise" in result
    assert "test message" in result
