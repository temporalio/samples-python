from activity_sessions import StepEvent
from activity_sessions.single_session import Lifecycle


def test_lifecycle_tracks_binding_and_progress() -> None:
    life = Lifecycle(["a", "b"], steps=2)
    for event in [StepEvent("a", 0, "a1", 0), StepEvent("a", 1, "a1", 0)]:
        life.turns.events[event.workflow_id, event.step] = event
    assert life.progress() == {"a": 2, "b": 0}
    assert life.worker_of("a") == "a1" and life.worker_of("b") is None
