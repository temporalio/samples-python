"""Stream model output to a subscriber outside the Workflow.

``TemporalChatClient(streaming_topic="events")`` makes every model call of that
client run as the streaming Activity, which publishes each update to the
``events`` topic of a ``WorkflowStream`` hosted on the Workflow, batched every
100 milliseconds. The Workflow still gets the whole response, so the result is
the same as without a topic.
"""

# @@@SNIPSTART python-microsoft-agent-framework-streaming-workflow
from datetime import timedelta

from agent_framework import Agent
from temporalio import workflow
from temporalio.contrib.workflow_streams import WorkflowStream
from temporalio.microsoft_agent_framework import TemporalChatClient

STREAMING_TOPIC = "events"


@workflow.defn
class StreamingWorkflow:
    def __init__(self) -> None:
        # Host the stream so the model Activity has somewhere to publish.
        self._stream = WorkflowStream()

    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            client=TemporalChatClient(
                "gpt-4o-mini",
                start_to_close_timeout=timedelta(seconds=60),
                streaming_topic=STREAMING_TOPIC,
            ),
            instructions="You are a concise assistant.",
        )
        # With a topic set, this call runs as the streaming Activity and
        # publishes its updates, with or without stream=True.
        response = await agent.run(prompt)
        return response.text


# @@@SNIPEND
