import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.graph_api.human_in_the_loop.workflow import (
    ChatbotWorkflow,
    chatbot_graph,
)


async def test_human_in_the_loop_approve(client: Client) -> None:
    task_queue = f"hitl-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(graphs=[chatbot_graph])

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
    plugin = LangGraphPlugin(graphs=[chatbot_graph])

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
        await handle.signal(ChatbotWorkflow.provide_feedback, "please be more concise")
        result = await handle.result()

    assert "[Revised]" in result
    assert "please be more concise" in result
