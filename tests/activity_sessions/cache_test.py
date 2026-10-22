from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from temporalio.testing import ActivityEnvironment

from activity_sessions.activities import ConversationActivities


async def test_same_worker_loads_context_once() -> None:
    activities = ConversationActivities("worker-1", True, Path("context.txt"))
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_run_id="run-1")
    with patch.object(Path, "read_text", return_value="Conversation context") as read:
        first = await env.run(activities.conversation_step, 1)
        second = await env.run(activities.conversation_step, 2)
        third = await env.run(activities.conversation_step, 3)
    assert [first.cache_hit, second.cache_hit, third.cache_hit] == [False, True, True]
    read.assert_called_once()


async def test_other_worker_has_its_own_cache(tmp_path: Path) -> None:
    context_file = tmp_path / "context.txt"
    context_file.write_text("Conversation context")
    first_worker = ConversationActivities("worker-1", True, context_file)
    other_worker = ConversationActivities("worker-2", False, context_file)
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_run_id="run-1")
    first = await env.run(first_worker.conversation_step, 1)
    second = await env.run(other_worker.conversation_step, 2)
    third = await env.run(first_worker.conversation_step, 3)
    assert [first.cache_hit, second.cache_hit, third.cache_hit] == [False, False, True]
    assert first_worker.cache is not other_worker.cache
    assert other_worker.cache["run-1"] == "Conversation context"


async def test_new_run_starts_cold_on_same_worker() -> None:
    activities = ConversationActivities("worker-1", True, Path("context.txt"))
    env = ActivityEnvironment()
    with patch.object(Path, "read_text", return_value="Conversation context") as read:
        env.info = replace(env.info, workflow_run_id="run-1")
        await env.run(activities.conversation_step, 1)
        env.info = replace(env.info, workflow_run_id="run-2")
        result = await env.run(activities.conversation_step, 1)
    assert not result.cache_hit
    assert read.call_count == 2
