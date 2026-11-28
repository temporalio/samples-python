import asyncio
import json
import uuid
from pathlib import Path

import pytest
from temporalio import activity
from temporalio.client import (
    Client,
    StreamConfig,
    WorkflowFailureError,
    WorkflowHandle,
    WorkflowHistory,
)
from temporalio.exceptions import CancelledError, TerminatedError
from temporalio.nexus.system.stream_service import StreamRef
from temporalio.testing import MemoryStreamStore
from temporalio.worker import Replayer, Worker
from temporalio_streams_redis import RedisStreamStore

from streams_redis import run_agent
from streams_redis.activities.model_activity import ANSWER, stream_answer
from streams_redis.run_agent import QUESTION, run
from streams_redis.shared import LAST_EVENT, TASK_QUEUE, AgentEvent
from streams_redis.workflows.agent_workflow import AgentWorkflow


@pytest.mark.parametrize("after_completion", [False, True], ids=["live", "completed"])
async def test_a_reader_resumes_at_its_offset(
    client: Client, redis_url: str, monkeypatch, after_completion: bool
):
    config = client.config()
    config["stream_config"] = StreamConfig(stores=[RedisStreamStore(redis_url)])

    async def connect() -> Client:
        return Client(**config)

    if after_completion:
        completed = asyncio.Event()
        result = WorkflowHandle.result
        read = run_agent.read_and_resume

        async def observe_completion(self, *args, **kwargs):
            answer = await result(self, *args, **kwargs)
            completed.set()
            return answer

        async def delayed_read(*args, **kwargs):
            await completed.wait()
            return await read(*args, **kwargs)

        monkeypatch.setattr(WorkflowHandle, "result", observe_completion)
        monkeypatch.setattr(run_agent, "read_and_resume", delayed_read)

    async with Worker(
        await connect(),
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],
        activities=[stream_answer],
    ):
        async with asyncio.timeout(15):
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
    read_done = asyncio.Event()
    result = WorkflowHandle.result

    async def result_after_read(self, *args, **kwargs):
        # Force the final-event path instead of racing Workflow result delivery.
        await read_done.wait()
        return await result(self, *args, **kwargs)

    monkeypatch.setattr(WorkflowHandle, "result", result_after_read)

    async def cancel_then_follow(client, stream_ref, **kwargs):
        await client.get_workflow_handle(stream_ref.id).cancel()
        page, offset = await follow(client, stream_ref, **kwargs)
        events.extend(page)
        read_done.set()
        return page, offset

    monkeypatch.setattr(run_agent, "follow", cancel_then_follow)

    async def connect() -> Client:
        assert not events, "the reader reconnected after Done"
        return client

    # Keep the Activity queued so cancellation reaches the Workflow before four events.
    async with Worker(client, task_queue=TASK_QUEUE, workflows=[AgentWorkflow]):
        async with asyncio.timeout(15):
            with pytest.raises(WorkflowFailureError) as failure:
                await run(connect)

    assert isinstance(failure.value.cause, CancelledError)
    assert 0 < len(events) < 4
    assert events[-1] == LAST_EVENT


async def test_cancellation_after_a_token_leaves_done_last(
    client: Client, redis_url: str
):
    config = client.config()
    config["stream_config"] = StreamConfig(stores=[RedisStreamStore(redis_url)])
    client = Client(**config)
    stopped = asyncio.Event()

    @activity.defn(name="stream_answer")
    async def tracked_answer(stream_ref: StreamRef[AgentEvent]) -> str:
        try:
            return await stream_answer(stream_ref)
        finally:
            stopped.set()

    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],
        activities=[tracked_answer],
    ):
        async with asyncio.timeout(15):
            handle = await client.start_workflow(
                AgentWorkflow.run, QUESTION, id=str(uuid.uuid4()), task_queue=TASK_QUEUE
            )
            stream = client.get_stream(
                await handle.execute_update(AgentWorkflow.stream_ref)
            )
            async for record in stream.read():
                if record.body.kind == "token":
                    break
            await handle.cancel()
            with pytest.raises(WorkflowFailureError) as failure:
                await handle.result()
            await stopped.wait()
            page = await stream.read_page()

    assert isinstance(failure.value.cause, CancelledError)
    assert page.records[-1].body == LAST_EVENT


async def test_replay_cancellation_before_activity_acknowledgement():
    history = json.loads(
        Path(__file__).with_name("cancellation_history.json").read_text()
    )
    started = history["events"][0]["workflowExecutionStartedEventAttributes"]
    await Replayer(
        workflows=[AgentWorkflow],
        stream_config=StreamConfig(stores=[MemoryStreamStore(name="redis")]),
    ).replay_workflow(WorkflowHistory.from_json(started["workflowId"], history))


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
