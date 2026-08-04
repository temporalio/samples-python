"""Stream Gemini output to an external subscriber via WorkflowStream.

``TemporalAsyncClient(streaming_topic="gemini")`` publishes each
``generate_content_stream`` chunk onto a workflow-hosted ``WorkflowStream`` as
it arrives, so external consumers can watch the model produce text in real time
while the workflow runs durably. The workflow holds itself open on a ``finish``
signal so a subscriber can reliably read the stream before the run completes.
"""

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient
from temporalio.contrib.workflow_streams import WorkflowStream

# A subscriber that crashes before signaling should not pin the workflow open.
FINISH_TIMEOUT = timedelta(minutes=5)


# @@@SNIPSTART python-google-genai-streaming-workflow
@workflow.defn
class StreamingWorkflow:
    @workflow.init
    def __init__(self, prompt: str) -> None:
        # Hosting a WorkflowStream is required when streaming_topic is set.
        self.stream = WorkflowStream()
        self._done = False

    @workflow.run
    async def run(self, prompt: str) -> str:
        client = TemporalAsyncClient(streaming_topic="gemini")
        chunks: list[str] = []
        async for chunk in await client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
        ):
            chunks.append(chunk.text or "")
        # Bound the wait: if the subscriber dies without signaling, complete
        # anyway instead of waiting forever.
        try:
            await workflow.wait_condition(lambda: self._done, timeout=FINISH_TIMEOUT)
        except asyncio.TimeoutError:
            workflow.logger.warning(
                "No finish signal after %s; completing without a subscriber.",
                FINISH_TIMEOUT,
            )
        return "".join(chunks)

    @workflow.signal
    def finish(self) -> None:
        self._done = True


# @@@SNIPEND
