"""Stream model output to external subscribers while keeping a durable result.

Constructing the plugin with ``DeepAgentsPlugin(streaming_topic=...)`` flips
model dispatch from ``deepagents.invoke_model`` to
``deepagents.invoke_model_streaming``: the streaming activity coalesces chunk
batches and publishes them to a ``temporalio.contrib.workflow_streams`` topic for
subscribers, while the aggregated final message is still returned to the workflow
(so the durable result is identical to the non-streaming path).

Streaming is async-only, so the workflow drives an explicit
``TemporalModel.astream(...)``. It hosts a ``WorkflowStream`` so external
subscribers can attach by workflow id (see ``run_workflow.py``).
"""

# @@@SNIPSTART python-deepagents-streaming-workflow
from langchain_core.messages import HumanMessage
from temporalio import workflow
from temporalio.contrib.deepagents import TemporalModel
from temporalio.contrib.workflow_streams import WorkflowStream

STREAMING_TOPIC = "model-chunks"


@workflow.defn
class StreamingWorkflow:
    def __init__(self) -> None:
        # Host the stream so the publish-Signal handler is registered before the
        # streaming activity (the external publisher) starts publishing.
        self.stream = WorkflowStream()

    @workflow.run
    async def run(self, prompt: str) -> str:
        model = TemporalModel(model="anthropic:claude-sonnet-4-5")
        parts: list[str] = []
        async for chunk in model.astream([HumanMessage(content=prompt)]):
            parts.append(str(chunk.content))
        return "".join(parts)


# @@@SNIPEND
