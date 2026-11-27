import queue

from activity_sessions import StepEvent
from activity_sessions.fleet import Turns


def test_turns_keep_the_latest_event_per_step() -> None:
    events: "queue.Queue[StepEvent]" = queue.Queue()
    for event in [
        StepEvent("a", 1, "w1", 0),
        StepEvent("a", 0, "w1", 0),
        StepEvent("b", 0, "w2", 0),
        # A retried turn replaces its earlier event.
        StepEvent("a", 1, "w2", 1),
    ]:
        events.put(event)
    turns = Turns()
    turns.drain(events)  # type: ignore[arg-type]
    assert [event.worker for event in turns.of("a")] == ["w1", "w2"]
    assert turns.workflows_by_worker() == {"w1": {"a"}, "w2": {"a", "b"}}
