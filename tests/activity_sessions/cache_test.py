from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from temporalio.testing import ActivityEnvironment

from activity_sessions.activities import ConversationActivities
from activity_sessions.models import ConversationContext, StepInput, WorkerRegistration
from activity_sessions.storage import FileArtifactStore


async def test_next_step_reuses_locally_cached_output(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path)
    initial_ref = store.write(ConversationContext(["Conversation context"]))
    activities = ConversationActivities(store, "worker-1", True)
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_run_id="run-1")
    with (
        patch.object(store, "read", wraps=store.read) as reads,
        patch.object(store, "write", wraps=store.write) as writes,
    ):
        first = await env.run(
            activities.process_conversation_step, StepInput(1, initial_ref)
        )
        second = await env.run(
            activities.process_conversation_step, StepInput(2, first.output_ref)
        )
        assert not first.cache_hit
        assert second.cache_hit
        assert reads.call_count == first.artifact_reads + second.artifact_reads == 1
        assert writes.call_count == first.artifact_writes + second.artifact_writes == 2
    assert store.read(second.output_ref).completed_steps == [1, 2]
    assert store.read(initial_ref).completed_steps == []


async def test_new_worker_recovers_output_from_external_store(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path)
    initial_ref = store.write(ConversationContext(["Conversation context"]))
    producer = ConversationActivities(store, "worker-1", True)
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_run_id="run-1")
    first = await env.run(producer.process_conversation_step, StepInput(1, initial_ref))

    consumer_store = FileArtifactStore(tmp_path)
    consumer = ConversationActivities(consumer_store, "worker-2", False)
    with patch.object(consumer_store, "read", wraps=consumer_store.read) as reads:
        second = await env.run(
            consumer.process_conversation_step, StepInput(2, first.output_ref)
        )
    assert not second.cache_hit
    assert reads.call_count == second.artifact_reads == 1
    assert not second.session_enabled
    assert consumer_store.read(second.output_ref).completed_steps == [1, 2]


async def test_new_workflow_run_starts_cold_on_same_worker(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path)
    initial_ref = store.write(ConversationContext(["Conversation context"]))
    activities = ConversationActivities(store, "worker-1", True)
    env = ActivityEnvironment()
    env.info = replace(env.info, workflow_run_id="run-1")
    await env.run(activities.process_conversation_step, StepInput(1, initial_ref))
    env.info = replace(env.info, workflow_run_id="run-2")
    result = await env.run(
        activities.process_conversation_step, StepInput(1, initial_ref)
    )
    assert not result.cache_hit
    assert result.artifact_reads == 1


def test_artifact_integrity_and_safe_references(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path)
    reference = store.write(ConversationContext(["Conversation context"]))
    with pytest.raises(ValueError, match="SHA-256"):
        store.read("../outside-store")
    (store.artifacts / f"{reference}.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum mismatch"):
        store.read(reference)


def test_roster_preserves_worker_capabilities_and_removes_only_its_registration(
    tmp_path: Path,
) -> None:
    store = FileArtifactStore(tmp_path)
    session = WorkerRegistration("worker-1", True, 101, "queue")
    ordinary = WorkerRegistration("worker-2", False, 102, "queue")
    store.register_worker(session)
    store.register_worker(ordinary)
    assert store.list_workers("queue") == [session, ordinary]
    assert store.list_workers("another-queue") == []
    with pytest.raises(ValueError, match="already registered"):
        store.register_worker(session)
    store.unregister_worker(replace(session, pid=999))
    assert store.list_workers("queue") == [session, ordinary]
    store.unregister_worker(session)
    store.unregister_worker(ordinary)
    assert store.list_workers("queue") == []
