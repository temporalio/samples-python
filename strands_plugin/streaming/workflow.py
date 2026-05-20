"""Workflow that streams model chunks to an external subscriber.

``TemporalAgent(streaming_topic="events")`` publishes each ``StreamEvent`` from
inside the model activity onto a workflow-hosted ``WorkflowStream``.
Subscribers connect via ``WorkflowStreamClient`` and read the topic in real
time. Chunks are batched on the ``streaming_batch_interval`` (default 100ms).
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.strands import TemporalAgent
from temporalio.contrib.workflow_streams import WorkflowStream


@workflow.defn
class StreamingWorkflow:
    def __init__(self) -> None:
        # Hosting the stream on the workflow is what makes the topic addressable
        # by ``WorkflowStreamClient``.
        self.stream = WorkflowStream()
        self.agent = TemporalAgent(
            start_to_close_timeout=timedelta(seconds=60),
            streaming_topic="events",
        )

    @workflow.run
    async def run(self, prompt: str) -> str:
        result = await self.agent.invoke_async(prompt)
        return str(result)
