from dataclasses import replace

from temporalio.testing import ActivityEnvironment

from activity_sessions import StepEvent
from activity_sessions.activities import ConversationActivities


def environment(run_id: str) -> ActivityEnvironment:
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_id="workflow-1", workflow_run_id=run_id)
    return env


def finished_hits(events: list[StepEvent]) -> list[bool]:
    return [event.cache_hit for event in events if event.finished]


async def test_same_worker_loads_context_once() -> None:
    events: list[StepEvent] = []
    activities = ConversationActivities("worker-1", 0, events.append)
    env = environment("run-1")
    for step in (1, 2, 3):
        await env.run(activities.conversation_step, step)
    assert finished_hits(events) == [False, True, True]
    assert events[0] == StepEvent("workflow-1", 1, "worker-1", False, False)
    assert list(activities.cache) == ["run-1"]


async def test_other_worker_has_its_own_cache() -> None:
    events: list[StepEvent] = []
    first_worker = ConversationActivities("worker-1", 0, events.append)
    other_worker = ConversationActivities("worker-2", 0, events.append)
    env = environment("run-1")
    await env.run(first_worker.conversation_step, 1)
    await env.run(other_worker.conversation_step, 2)
    await env.run(first_worker.conversation_step, 3)
    assert finished_hits(events) == [False, False, True]
    assert first_worker.cache is not other_worker.cache
    assert "run-1" in other_worker.cache


async def test_new_run_starts_cold_on_same_worker() -> None:
    events: list[StepEvent] = []
    activities = ConversationActivities("worker-1", 0, events.append)
    await environment("run-1").run(activities.conversation_step, 1)
    await environment("run-2").run(activities.conversation_step, 1)
    assert finished_hits(events) == [False, False]
