"""Stream LLM output to the terminal, handling retries.

Starts a ``ChatWorkflow``, subscribes to its delta / complete / retry
topics, and renders the model's output to stdout as it arrives. On a
``RETRY`` event (the activity is on attempt > 1), the consumer rewinds
its rendered output with ANSI escapes and starts fresh — so a killed
worker doesn't leave a half-finished response stuck on screen
followed by the retried attempt's full output.

Requires ``OPENAI_API_KEY`` in the environment and the ``chat-stream``
extra::

    uv sync --group chat-stream
    export OPENAI_API_KEY=...

Run the chat worker first (``uv run workflow_streams/run_chat_worker.py``),
then::

    uv run workflow_streams/run_chat.py

To see retry handling in action, kill the chat worker mid-stream
(Ctrl-C in its terminal) and start it again. The consumer will clear
its accumulated output on the ``RETRY`` event and re-render the
retried attempt's output from scratch.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from temporalio.client import Client
from temporalio.common import RawValue
from temporalio.contrib.workflow_streams import WorkflowStreamClient

from workflow_streams.chat_shared import (
    CHAT_TASK_QUEUE,
    TOPIC_COMPLETE,
    TOPIC_DELTA,
    TOPIC_RETRY,
    ChatInput,
    RetryEvent,
    TextComplete,
    TextDelta,
)
from workflow_streams.workflows.chat_workflow import ChatWorkflow

# A prompt long enough that you can comfortably kill the worker
# mid-stream and watch the retry render. Adjust to taste.
DEFAULT_PROMPT = (
    "Write a 250-word friendly explainer for a new engineer about why "
    "durable execution matters in distributed systems. Use short "
    "paragraphs and a couple of concrete examples."
)


def _ansi_clear(line_count: int) -> None:
    """Move the cursor up `line_count` lines and clear to end of screen.

    Used on RETRY to throw away the failed attempt's rendered output
    before the retried attempt starts. Counts logical newlines in the
    rendered text; a long line that wraps in the terminal won't be
    fully cleared by this — accept the rough edges, ``rich`` would do
    it cleanly but we are deliberately stdlib-only here.
    """
    sys.stdout.write("\r")
    if line_count > 0:
        sys.stdout.write(f"\033[{line_count}A")
    sys.stdout.write("\033[J")
    sys.stdout.flush()


async def main() -> None:
    client = await Client.connect("localhost:7233")
    converter = client.data_converter.payload_converter

    workflow_id = f"workflow-stream-chat-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        ChatWorkflow.run,
        ChatInput(prompt=DEFAULT_PROMPT),
        id=workflow_id,
        task_queue=CHAT_TASK_QUEUE,
    )

    stream = WorkflowStreamClient.create(client, workflow_id)

    # Subscribe to all three topics on a single iterator. result_type=
    # RawValue lets us dispatch on item.topic and decode against the
    # right dataclass per topic.
    accumulated: list[str] = []
    async for item in stream.subscribe(
        [TOPIC_DELTA, TOPIC_RETRY, TOPIC_COMPLETE],
        result_type=RawValue,
    ):
        if item.topic == TOPIC_RETRY:
            evt = converter.from_payload(item.data.payload, RetryEvent)
            line_count = "".join(accumulated).count("\n")
            _ansi_clear(line_count)
            print(f"[retry attempt {evt.attempt}] resetting output\n")
            accumulated.clear()
        elif item.topic == TOPIC_DELTA:
            delta = converter.from_payload(item.data.payload, TextDelta)
            accumulated.append(delta.text)
            sys.stdout.write(delta.text)
            sys.stdout.flush()
        elif item.topic == TOPIC_COMPLETE:
            # Newline so the prompt isn't on the same line as the
            # last delta. The TextComplete payload is the full text
            # (also returned by the workflow), but the consumer has
            # already rendered it incrementally so we don't reprint.
            converter.from_payload(item.data.payload, TextComplete)
            print()
            break

    result = await handle.result()
    print(f"\n[workflow result: {len(result)} chars]")


if __name__ == "__main__":
    asyncio.run(main())
