import asyncio
import uuid
from datetime import timedelta

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.test import TestModel
from pydantic_ai.settings import ModelSettings
from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai_plugin.human_in_the_loop.workflow import (
    ApprovalInput,
    ApprovalWorkflow,
    Decision,
)
from pydantic_ai_plugin.tests.helpers import with_pydantic_ai


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


@pytest.mark.parametrize("decision", ["approve", "reject", "cancel"])
async def test_additional_approval_round(
    client: Client, monkeypatch: pytest.MonkeyPatch, decision: Decision
) -> None:
    second_round_requested = asyncio.Event()
    observed_returns: list[list[str]] = []

    async def request(
        self: TestModel,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        returns = [
            str(part.content)
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        observed_returns.append(returns)
        if len(returns) < 2:
            record_id = str(42 + len(returns))
            if returns:
                second_round_requested.set()
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "delete_record",
                        {"record_id": record_id},
                        tool_call_id=f"delete-{record_id}",
                    )
                ]
            )
        return ModelResponse(parts=[TextPart("Both decisions were applied.")])

    monkeypatch.setattr(TestModel, "request", request)
    client = with_pydantic_ai(client)
    task_queue = f"pydantic-ai-approval-rounds-{uuid.uuid4()}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[ApprovalWorkflow],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            ApprovalWorkflow.run,
            ApprovalInput(prompt="Delete records 42 and 43."),
            id=f"pydantic-ai-approval-rounds-{uuid.uuid4()}",
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=20),
        )
        for round_index in range(2):
            if round_index:
                await asyncio.wait_for(second_round_requested.wait(), timeout=5)
            for _ in range(100):
                if await handle.query(ApprovalWorkflow.pending_approval):
                    break
                await asyncio.sleep(0.05)
            else:
                raise AssertionError(
                    f"approval round {round_index + 1} was not requested"
                )
            await handle.signal(
                ApprovalWorkflow.decide, "approve" if round_index == 0 else decision
            )
        result = await asyncio.wait_for(handle.result(), timeout=5)

    assert observed_returns[:2] == [[], ["deleted 42"]]
    if decision == "cancel":
        assert result == "Cancelled by the operator."
        assert len(observed_returns) == 2
    else:
        assert result == "Both decisions were applied."
        assert observed_returns[2] == [
            "deleted 42",
            "deleted 43" if decision == "approve" else "Rejected by the operator.",
        ]
