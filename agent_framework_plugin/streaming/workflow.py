"""Stream model output to a subscriber outside the Workflow.

``TemporalChatClient(streaming_topic="events")`` makes the model Activity
publish every update to the ``events`` topic of a ``WorkflowStream`` hosted on
the Workflow, batched every 100 milliseconds. The Workflow still gets the whole
response, so the result is the same as without streaming.
"""

# @@@SNIPSTART python-agent-framework-streaming-workflow
from datetime import timedelta

from agent_framework import Agent
from temporalio import workflow
from temporalio.agent_framework import TemporalChatClient
from temporalio.contrib.workflow_streams import WorkflowStream

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
        # stream=True selects the streaming Activity; the final response is the same.
        response = await agent.run(prompt, stream=True).get_final_response()
        return response.text


# @@@SNIPEND
