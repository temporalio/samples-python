"""Streaming with the LangGraph Graph API and Temporal Workflow Streams.

A workflow's :class:`WorkflowStream` is a durable, offset-addressed event channel
external clients can subscribe to while the workflow is still running. This sample
demonstrates both ways the LangGraph plugin produces stream items:

- **Node token streaming** -- the ``write_story`` node calls LangGraph's
  ``get_stream_writer()`` to emit fine-grained tokens. The plugin is configured with
  ``streaming_topic="tokens"`` (see ``run_worker.py``), which routes those writes onto
  the ``"tokens"`` topic.
- **Workflow-side ``astream`` publish** -- the workflow drives the graph with
  ``app.astream(...)`` and publishes each node-completion chunk onto a ``"progress"``
  topic it owns.

A single client subscribes to all topics and demultiplexes on ``item.topic``.
"""

from datetime import timedelta

from langgraph.config import get_stream_writer
from langgraph.graph import START, StateGraph
from temporalio import workflow
from temporalio.contrib.langgraph import graph as temporal_graph
from temporalio.contrib.workflow_streams import WorkflowStream
from typing_extensions import TypedDict


class State(TypedDict):
    topic: str
    story: str


async def outline(state: State) -> dict[str, str]:
    """Produce a short opening line. Runs first so ``astream`` emits an early chunk."""
    return {"story": f"A story about {state['topic']}:"}


async def write_story(state: State) -> dict[str, str]:
    """Write the story, emitting each word as a token via the stream writer."""
    writer = get_stream_writer()
    words = f"{state['story']} Once upon a time, there was {state['topic']}.".split()
    for word in words:
        writer({"token": word + " "})
    return {"story": " ".join(words)}


def make_streaming_graph() -> StateGraph:
    g = StateGraph(State)
    activity_metadata = {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=10),
    }
    g.add_node("outline", outline, metadata=activity_metadata)
    g.add_node("write_story", write_story, metadata=activity_metadata)
    g.add_edge(START, "outline")
    g.add_edge("outline", "write_story")
    return g


@workflow.defn
class StreamingWorkflow:
    def __init__(self) -> None:
        # WorkflowStream must be constructed during workflow initialization.
        self.stream = WorkflowStream()
        self._stream_acked = False

    @workflow.signal
    def ack_stream(self) -> None:
        """Signalled by the client once it has finished consuming the stream."""
        self._stream_acked = True

    @workflow.run
    async def run(self, topic: str) -> str:
        app = temporal_graph("streaming").compile()
        progress = self.stream.topic("progress")

        story = ""
        async for chunk in app.astream({"topic": topic, "story": ""}):
            # Each chunk is {node_name: {state updates}}. Forward it as progress.
            progress.publish(chunk)
            for node_update in chunk.values():
                if "story" in node_update:
                    story = node_update["story"]

        progress.publish({"done": True})

        # The stream disappears when the workflow completes, so wait until the
        # client acknowledges it has finished consuming before returning.
        await workflow.wait_condition(lambda: self._stream_acked)
        return story
