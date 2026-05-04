from __future__ import annotations

from datetime import timedelta

from openai import AsyncOpenAI
from temporalio import activity
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from workflow_streams.llm_shared import (
    TOPIC_COMPLETE,
    TOPIC_DELTA,
    TOPIC_RETRY,
    LLMInput,
    RetryEvent,
    TextComplete,
    TextDelta,
)


@activity.defn
async def stream_completion(input: LLMInput) -> str:
    """Stream an LLM completion to the parent workflow's stream.

    Activity-as-publisher: each delta from the OpenAI streaming API is
    pushed to the workflow's stream as a ``TextDelta`` event on the
    ``delta`` topic. The accumulated full text returns as the
    activity's result and is also published on the ``complete`` topic
    as a terminator. On retry attempts (``activity.info().attempt > 1``)
    a ``RetryEvent`` lands on the ``retry`` topic before the new
    attempt's deltas, so consumers can reset their accumulated state
    instead of concatenating the failed attempt's partial output with
    the retried attempt's full output.

    No ``force_flush=True``: the 200ms ``batch_interval`` is fast
    enough for an interactive feel, and the WorkflowStreamClient's
    ``__aexit__`` cancels a sleeping flusher cleanly.
    """
    stream_client = WorkflowStreamClient.from_within_activity(
        batch_interval=timedelta(milliseconds=200),
    )
    # Disable provider-side retries; let Temporal own retry policy at
    # the activity layer.
    openai_client = AsyncOpenAI(max_retries=0)

    async with stream_client:
        deltas = stream_client.topic(TOPIC_DELTA, type=TextDelta)
        complete = stream_client.topic(TOPIC_COMPLETE, type=TextComplete)
        retry = stream_client.topic(TOPIC_RETRY, type=RetryEvent)

        attempt = activity.info().attempt
        if attempt > 1:
            retry.publish(RetryEvent(attempt=attempt))

        full: list[str] = []
        oai_stream = await openai_client.chat.completions.create(
            model=input.model,
            messages=[{"role": "user", "content": input.prompt}],
            stream=True,
        )
        async for chunk in oai_stream:
            if not chunk.choices:
                continue
            text = chunk.choices[0].delta.content
            if not text:
                continue
            deltas.publish(TextDelta(text=text))
            full.append(text)

        full_text = "".join(full)
        complete.publish(TextComplete(full_text=full_text))
    return full_text
