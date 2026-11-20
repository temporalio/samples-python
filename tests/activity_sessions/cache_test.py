from dataclasses import replace

from temporalio.testing import ActivityEnvironment

from activity_sessions import StepEvent
from activity_sessions.activities import ConversationActivities


def environment(run_id: str) -> ActivityEnvironment:
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_id="workflow-1", workflow_run_id=run_id)
    return env


def worker(name: str, events: list[StepEvent]) -> ConversationActivities:
    return ConversationActivities(name, 0, 0, events.append)


async def test_same_worker_never_fetches_its_own_turns() -> None:
    events: list[StepEvent] = []
    activities = worker("w1", events)
    env = environment("run-1")
    for step in range(3):
        await env.run(activities.conversation_step, step)
    assert [event.fetched for event in events] == [0, 0, 0]
    assert len(activities.cache["run-1"]) == 3


async def test_stale_or_cold_worker_fetches_only_missing_turns() -> None:
    events: list[StepEvent] = []
    worker_a, worker_b = worker("w1", events), worker("w2", events)
    env = environment("run-1")
    await env.run(worker_a.conversation_step, 0)
    await env.run(worker_b.conversation_step, 1)
    await env.run(worker_a.conversation_step, 2)
    # w2 lacks turn 0; w1 returns holding turn 0 but not turn 1.
    assert [event.fetched for event in events] == [0, 1, 1]
