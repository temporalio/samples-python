import asyncio
import uuid

import pytest
from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.human_in_the_loop.workflow import (
    ApprovalInput,
    ApprovalWorkflow,
    Decision,
)
from tests.pydantic_ai_plugin.helpers import with_pydantic_ai


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        ("approve", "The operator decision was applied."),
        ("reject", "The operator decision was applied."),
        ("cancel", "Cancelled by the operator."),
    ],
)
async def test_operator_decision(
    client: Client, decision: Decision, expected: str
) -> None:
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-approval-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ApprovalWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            ApprovalWorkflow.run,
            ApprovalInput(prompt="Delete the record."),
            id=f"pydantic-ai-approval-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        for _ in range(100):
            if await handle.query(ApprovalWorkflow.pending_approval):
                break
            await asyncio.sleep(0.05)
        else:
            raise AssertionError("approval was not requested")
        await handle.signal(ApprovalWorkflow.decide, decision)
        result = await handle.result()

    assert result == expected
