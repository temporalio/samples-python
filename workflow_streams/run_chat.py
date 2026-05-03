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

# Long enough that you can comfortably kill the worker mid-stream and
# watch the retry render. Adjust to taste.
DEFAULT_PROMPT = (
    "Write a 500-word comparison of Paxos, Raft, and Viewstamped "
    "Replication for a new distributed-systems engineer. Cover the "
    "core ideas, leader election, normal-case operation, "
    "reconfiguration, and the practical tradeoffs that show up when "
    "implementing each. Use short paragraphs."
)


# ANSI cursor save / restore. ``\033[s`` saves the current cursor
# position, ``\033[u`` restores it, ``\033[J`` clears from the cursor
# to the end of the screen. Save once before the first delta, and on
# RETRY restore + clear-to-end so the failed attempt's rendered output
# disappears regardless of how it was wrapped by the terminal. Save
# again afterwards so a second retry can rewind to the same point.
ANSI_SAVE = "\033[s"
ANSI_RESTORE_AND_CLEAR = "\033[u\033[J"


async def main() -> None:
    client = await Client.connect("localhost:7233")
    converter = client.data_converter.payload_converter

    workflow_id = f"workflow-stream-chat-{uuid.uuid4().hex[:8]}"
    chat_input = ChatInput(prompt=DEFAULT_PROMPT)
    handle = await client.start_workflow(
        ChatWorkflow.run,
        chat_input,
        id=workflow_id,
        task_queue=CHAT_TASK_QUEUE,
    )

    # Print a header so the user sees something immediately. The
    # response will start streaming below it once the first delta
    # arrives — until then this is the only line on screen.
    print(
        f"[chat {workflow_id}] streaming response from {chat_input.model}, "
        f"awaiting first token..."
    )
    print()
    sys.stdout.write(ANSI_SAVE)
    sys.stdout.flush()

    stream = WorkflowStreamClient.create(client, workflow_id)

    # Subscribe to all three topics on a single iterator.
    # result_type=RawValue lets us dispatch on item.topic and decode
    # against the right dataclass per topic.
    async for item in stream.subscribe(
        [TOPIC_DELTA, TOPIC_RETRY, TOPIC_COMPLETE],
        result_type=RawValue,
    ):
        if item.topic == TOPIC_RETRY:
            evt = converter.from_payload(item.data.payload, RetryEvent)
            sys.stdout.write(ANSI_RESTORE_AND_CLEAR)
            sys.stdout.flush()
            print(f"[retry attempt {evt.attempt}] resetting output")
            print()
            sys.stdout.write(ANSI_SAVE)
            sys.stdout.flush()
        elif item.topic == TOPIC_DELTA:
            delta = converter.from_payload(item.data.payload, TextDelta)
            sys.stdout.write(delta.text)
            sys.stdout.flush()
        elif item.topic == TOPIC_COMPLETE:
            # The full text is also in the payload (and returned by
            # the workflow), but the consumer has already rendered it
            # incrementally. Just terminate the line.
            converter.from_payload(item.data.payload, TextComplete)
            print()
            break

    result = await handle.result()
    print(f"\n[workflow result: {len(result)} chars]")


if __name__ == "__main__":
    asyncio.run(main())
