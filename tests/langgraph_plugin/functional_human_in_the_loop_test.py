import asyncio
import sys
import uuid
from unittest.mock import patch

import pytest
from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.human_in_the_loop.workflow import (
    ChatbotFunctionalWorkflow,
    activity_options,
    all_tasks,
    chatbot_entrypoint,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="LangGraph Functional API and interrupt() require Python >= 3.11 for async context propagation",
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
    "langgraph_plugin.functional_api.human_in_the_loop.workflow.init_chat_model",
    _fake_init_chat_model,
)


async def test_functional_human_in_the_loop_approve(client: Client) -> None:
    task_queue = f"functional-hitl-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        entrypoints={"chatbot": chatbot_entrypoint},
        tasks=all_tasks,
        activity_options=activity_options,
    )

    with _patch_llm():
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatbotFunctionalWorkflow],
            plugins=[plugin],
        ):
            handle = await client.start_workflow(
                ChatbotFunctionalWorkflow.run,
                "test message",
                id=f"functional-hitl-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Poll for draft to be ready
            draft = None
            for _ in range(40):
                await asyncio.sleep(0.25)
                draft = await handle.query(ChatbotFunctionalWorkflow.get_draft)
                if draft is not None:
                    break
            assert draft is not None
            assert "test message" in draft

            # Approve
            await handle.signal(ChatbotFunctionalWorkflow.provide_feedback, "approve")
            result = await handle.result()

    assert result["response"] == draft


async def test_functional_human_in_the_loop_revise(client: Client) -> None:
    task_queue = f"functional-hitl-revise-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        entrypoints={"chatbot": chatbot_entrypoint},
        tasks=all_tasks,
        activity_options=activity_options,
    )

    with _patch_llm():
        async with Worker(
            client,
            task_queue=task_queue,
            workflows=[ChatbotFunctionalWorkflow],
            plugins=[plugin],
        ):
            handle = await client.start_workflow(
                ChatbotFunctionalWorkflow.run,
                "test message",
                id=f"functional-hitl-revise-{uuid.uuid4()}",
                task_queue=task_queue,
            )

            # Poll for draft
            draft = None
            for _ in range(40):
                await asyncio.sleep(0.25)
                draft = await handle.query(ChatbotFunctionalWorkflow.get_draft)
                if draft is not None:
                    break
            assert draft is not None

            # Send revision feedback
            await handle.signal(
                ChatbotFunctionalWorkflow.provide_feedback, "please be more concise"
            )
            result = await handle.result()

    # The revision task feeds the draft and feedback into the LLM; the echo
    # stand-in returns the revision prompt, which contains both.
    assert "please be more concise" in result["response"]
    assert "test message" in result["response"]
