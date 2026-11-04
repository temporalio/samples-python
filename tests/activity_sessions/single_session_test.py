from activity_sessions import StepEvent
from activity_sessions.single_session import Lifecycle


def test_lifecycle_states() -> None:
    life = Lifecycle(["a", "b", "c"], steps=2)
    for event in [
        StepEvent("a", 0, "a1", 0),
        StepEvent("a", 1, "a1", 0),
        StepEvent("b", 0, "a2", 0),
    ]:
        life.turns.events[event.workflow_id, event.step] = event
    life.alive = {"a1": False, "a2": False}
    assert life.progress() == {"a": 2, "b": 1, "c": 0}
    assert [life.state(w) for w in life.workflow_ids] == ["done", "stalled", "waiting"]
    life.alive["a2"] = True
    assert life.state("b") == "running" and life.worker_of("b") == "a2"
