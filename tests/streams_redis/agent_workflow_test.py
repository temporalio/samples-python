import asyncio

import pytest
from temporalio.client import Client, StreamConfig, WorkflowFailureError
from temporalio.exceptions import CancelledError, TerminatedError
from temporalio.worker import Worker
from temporalio_streams_redis import RedisStreamStore

from streams_redis import run_agent
from streams_redis.activities.model_activity import ANSWER, stream_answer
from streams_redis.run_agent import QUESTION, run
from streams_redis.shared import LAST_EVENT, TASK_QUEUE, AgentEvent
from streams_redis.workflows.agent_workflow import AgentWorkflow


async def test_a_reader_resumes_at_its_offset(client: Client, redis_url: str):
    config = client.config()
    config["stream_config"] = StreamConfig(stores=[RedisStreamStore(redis_url)])

    async def connect() -> Client:
        return Client(**config)

    async with Worker(
        await connect(),
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],
        activities=[stream_answer],
    ):
        events = await run(connect)

    assert events == [
        AgentEvent("status", f"Thinking about: {QUESTION}"),
        *(AgentEvent("token", word) for word in ANSWER.split()),
        AgentEvent("status", "Done"),
    ]


async def test_an_early_terminal_event_observes_the_workflow_result(
    client: Client, redis_url: str, monkeypatch
):
    config = client.config()
    config["stream_config"] = StreamConfig(stores=[RedisStreamStore(redis_url)])
    client = Client(**config)
    follow = run_agent.follow
    events = []

    async def cancel_then_follow(client, stream_ref, **kwargs):
        await client.get_workflow_handle(stream_ref.id).cancel()
        page, offset = await follow(client, stream_ref, **kwargs)
        events.extend(page)
        return page, offset

    monkeypatch.setattr(run_agent, "follow", cancel_then_follow)

    async def connect() -> Client:
        assert not events, "the reader reconnected after Done"
        return client

    # Keep the Activity queued so cancellation reaches the Workflow before four events.
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[AgentWorkflow]):
        with pytest.raises(WorkflowFailureError) as failure:
            await run(connect)

    assert isinstance(failure.value.cause, CancelledError)
    assert 0 < len(events) < 4
    assert events[-1] == LAST_EVENT


async def test_a_terminated_workflow_stops_its_reader(
    client: Client, redis_url: str, monkeypatch
):
    config = client.config()
    config["stream_config"] = StreamConfig(stores=[RedisStreamStore(redis_url)])
    client = Client(**config)
    follow = run_agent.follow
    reader_closed = asyncio.Event()

    async def terminate_then_follow(client, stream_ref, **kwargs):
        await client.get_workflow_handle(stream_ref.id).terminate()
        try:
            return await follow(client, stream_ref, **kwargs)
        finally:
            reader_closed.set()

    monkeypatch.setattr(run_agent, "follow", terminate_then_follow)

    async def connect() -> Client:
        return client

    # A queued Activity keeps the Workflow open without writing its final event.
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[AgentWorkflow]):
        async with asyncio.timeout(15):
            with pytest.raises(WorkflowFailureError) as failure:
                await run(connect)

    assert isinstance(failure.value.cause, TerminatedError)
    assert reader_closed.is_set()
