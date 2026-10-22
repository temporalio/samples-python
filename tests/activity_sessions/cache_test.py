from dataclasses import replace

from temporalio.testing import ActivityEnvironment

from activity_sessions import StepEvent
from activity_sessions.activities import ConversationActivities


def environment(run_id: str) -> ActivityEnvironment:
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_id="workflow-1", workflow_run_id=run_id)
    return env


def fetched(events: list[StepEvent]) -> list[int]:
    return [event.fetched for event in events if event.finished]


async def test_first_turn_needs_no_fetch() -> None:
    events: list[StepEvent] = []
    activities = ConversationActivities("worker-1", 0, events.append)
    await environment("run-1").run(activities.conversation_step, 0)
    assert events == [
        StepEvent("workflow-1", 0, "worker-1", 0, False),
        StepEvent("workflow-1", 0, "worker-1", 0, True),
    ]
    assert activities.cache["run-1"] == ["Turn 0 of workflow-1"]


async def test_same_worker_never_fetches_its_own_turns() -> None:
    events: list[StepEvent] = []
    activities = ConversationActivities("worker-1", 0, events.append)
    env = environment("run-1")
    for step in range(4):
        await env.run(activities.conversation_step, step)
    assert fetched(events) == [0, 0, 0, 0]
    assert len(activities.cache["run-1"]) == 4


async def test_stale_worker_fetches_only_missing_turns() -> None:
    events: list[StepEvent] = []
    worker_a = ConversationActivities("worker-1", 0, events.append)
    worker_b = ConversationActivities("worker-2", 0, events.append)
    env = environment("run-1")
    await env.run(worker_a.conversation_step, 0)
    await env.run(worker_b.conversation_step, 1)
    await env.run(worker_a.conversation_step, 2)
    # B lacks turn 0; A returns holding turn 0 but not turn 1.
    assert fetched(events) == [0, 1, 1]
    assert len(worker_a.cache["run-1"]) == 3
    assert len(worker_b.cache["run-1"]) == 2


async def test_cold_worker_fetches_whole_history() -> None:
    events: list[StepEvent] = []
    activities = ConversationActivities("worker-1", 0, events.append)
    await environment("run-1").run(activities.conversation_step, 4)
    assert fetched(events) == [4]


async def test_new_run_starts_with_empty_history() -> None:
    events: list[StepEvent] = []
    activities = ConversationActivities("worker-1", 0, events.append)
    await environment("run-1").run(activities.conversation_step, 0)
    await environment("run-2").run(activities.conversation_step, 1)
    assert fetched(events) == [0, 1]
