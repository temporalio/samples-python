import asyncio
import sys
import uuid

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


@pytest.fixture(autouse=True)
def _restore_tasks():
    original_funcs = [t.func for t in all_tasks]
    try:
        yield
    finally:
        for t, orig in zip(all_tasks, original_funcs):
            t.func = orig


async def test_functional_human_in_the_loop_approve(client: Client) -> None:
    task_queue = f"functional-hitl-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
        entrypoints={"chatbot": chatbot_entrypoint},
        tasks=all_tasks,
        activity_options=activity_options,
    )

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

    assert "[Revised]" in result["response"]
    assert "please be more concise" in result["response"]
