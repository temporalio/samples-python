import asyncio
import uuid

import pytest
from langchain_core.messages import AIMessage
from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.contrib.deepagents import DeepAgentsPlugin
from temporalio.contrib.deepagents.testing import mock_model_provider
from temporalio.worker import Worker

from deepagents_plugin.human_in_the_loop.workflow import HumanInTheLoopAgent
from tests.deepagents_plugin.helpers import INVOKE_TOOL, count_scheduled_activities


async def test_human_in_the_loop_approve(client: Client) -> None:
    # First model turn asks to book the trip (the guarded tool → interrupt);
    # after the human approves, the second turn reports the booking.
    ask = AIMessage(
        content="",
        tool_calls=[{"name": "book_trip", "args": {"city": "Rome"}, "id": "c1"}],
    )
    done = AIMessage(content="Booked a trip to Rome.")
    plugin = DeepAgentsPlugin(model_provider=mock_model_provider([ask, done]))
    task_queue = f"deepagents-human-in-the-loop-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopAgent],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopAgent.run,
            "Rome",
            id=f"deepagents-human-in-the-loop-{uuid.uuid4()}",
            task_queue=task_queue,
        )

        # Wait for the agent to pause (surfaced via the query), then approve via
        # an update. Bounded poll so a regression fails fast.
        for _ in range(100):
            if await handle.query(HumanInTheLoopAgent.pending_approval) is not None:
                break
            await asyncio.sleep(0.1)
        else:
            raise AssertionError("workflow never surfaced the pending approval")

        await handle.execute_update(HumanInTheLoopAgent.resume, "approve")
        result = await handle.result()

    assert "Rome" in result
    # The approved book_trip really executed as an invoke_tool activity after
    # the resume — not just claimed by the scripted final message.
    counts = await count_scheduled_activities(handle)
    assert counts[INVOKE_TOOL] == 1, counts


async def test_resume_validator_rejects_invalid_decision(client: Client) -> None:
    # The workflow's documented contract: the update validator keeps decisions
    # other than approve/reject out of workflow history entirely.
    ask = AIMessage(
        content="",
        tool_calls=[{"name": "book_trip", "args": {"city": "Rome"}, "id": "c1"}],
    )
    done = AIMessage(content="Booked a trip to Rome.")
    plugin = DeepAgentsPlugin(model_provider=mock_model_provider([ask, done]))
    task_queue = f"deepagents-hitl-invalid-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopAgent],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopAgent.run,
            "Rome",
            id=f"deepagents-hitl-invalid-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        for _ in range(100):
            if await handle.query(HumanInTheLoopAgent.pending_approval) is not None:
                break
            await asyncio.sleep(0.1)
        else:
            raise AssertionError("workflow never surfaced the pending approval")

        with pytest.raises(WorkflowUpdateFailedError):
            await handle.execute_update(HumanInTheLoopAgent.resume, "maybe")

        # The workflow is still healthy and resumable after the rejection.
        await handle.execute_update(HumanInTheLoopAgent.resume, "approve")
        assert "Rome" in await handle.result()


async def test_human_in_the_loop_reject(client: Client) -> None:
    # The reject path: the guarded tool must never execute, and the agent
    # reports back based on the rejection.
    ask = AIMessage(
        content="",
        tool_calls=[{"name": "book_trip", "args": {"city": "Rome"}, "id": "c1"}],
    )
    final = AIMessage(content="Understood — not booking the trip.")
    plugin = DeepAgentsPlugin(model_provider=mock_model_provider([ask, final]))
    task_queue = f"deepagents-hitl-reject-{uuid.uuid4()}"

    config = client.config()
    config["plugins"] = [*config["plugins"], plugin]
    client = Client(**config)

    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[HumanInTheLoopAgent],
        max_cached_workflows=0,
    ):
        handle = await client.start_workflow(
            HumanInTheLoopAgent.run,
            "Rome",
            id=f"deepagents-hitl-reject-{uuid.uuid4()}",
            task_queue=task_queue,
        )
        for _ in range(100):
            if await handle.query(HumanInTheLoopAgent.pending_approval) is not None:
                break
            await asyncio.sleep(0.1)
        else:
            raise AssertionError("workflow never surfaced the pending approval")

        await handle.execute_update(HumanInTheLoopAgent.resume, "reject")
        result = await handle.result()

    assert "not booking" in result.lower()
    counts = await count_scheduled_activities(handle)
    # The rejected tool never ran as an activity.
    assert counts[INVOKE_TOOL] == 0, counts
