"""Stream Gemini output to an external subscriber via WorkflowStream.

``TemporalAsyncClient(streaming_topic="gemini")`` publishes each
``generate_content_stream`` chunk onto a workflow-hosted ``WorkflowStream`` as
it arrives, so external consumers can watch the model produce text in real time
while the workflow runs durably. The workflow holds itself open on a ``finish``
signal so a subscriber can reliably read the stream before the run completes.
"""

# @@@SNIPSTART python-google-genai-streaming-workflow
from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient
from temporalio.contrib.workflow_streams import WorkflowStream


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
        await workflow.wait_condition(lambda: self._done)
        return "".join(chunks)

    @workflow.signal
    def finish(self) -> None:
        self._done = True


# @@@SNIPEND
