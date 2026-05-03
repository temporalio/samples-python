from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.contrib.workflow_streams import WorkflowStream

from workflow_streams.chat_shared import ChatInput

with workflow.unsafe.imports_passed_through():
    from workflow_streams.activities.chat_activity import stream_completion


@workflow.defn
class ChatWorkflow:
    """Wrapper for an LLM-streaming activity.

    The workflow does no streaming of its own; it hosts the
    `WorkflowStream` so external subscribers can attach by workflow
    id, kicks off the streaming activity, and returns the full text
    the activity produced.

    Streaming is delegated to the activity because the OpenAI call is
    non-deterministic. If the activity fails partway through, Temporal
    retries it (up to ``max_attempts``); the retried attempt
    re-publishes from the start, so the consumer must reset on the
    activity's ``RETRY`` event. See
    `activities/chat_activity.py` and `run_chat.py`.
    """

    @workflow.init
    def __init__(self, input: ChatInput) -> None:
        # Construct the stream from `@workflow.init` so the
        # publish-Signal handler is registered before any external
        # publisher (the activity, here) tries to publish.
        self.stream = WorkflowStream(prior_state=input.stream_state)

    @workflow.run
    async def run(self, input: ChatInput) -> str:
        result = await workflow.execute_activity(
            stream_completion,
            input,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        # Hold the run open briefly so the consumer's next poll
        # delivers the activity's terminal `complete` event before the
        # workflow exits and the in-memory log is gone.
        await workflow.sleep(timedelta(milliseconds=500))
        return result
