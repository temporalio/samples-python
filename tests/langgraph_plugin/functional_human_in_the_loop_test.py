import asyncio
import uuid

from temporalio.client import Client
from temporalio.contrib.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from langgraph_plugin.functional_api.human_in_the_loop.workflow import (
    ChatbotFunctionalWorkflow,
    activity_options,
    all_tasks,
)


async def test_functional_human_in_the_loop_approve(client: Client) -> None:
    task_queue = f"functional-hitl-test-{uuid.uuid4()}"
    plugin = LangGraphPlugin(
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
