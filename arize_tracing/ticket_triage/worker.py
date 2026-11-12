"""Worker for the ticket triage sample."""

import argparse
import asyncio
import logging

from openinference.instrumentation.openai import OpenAIInstrumentor
from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from telemetry import force_flush, setup_tracing
from ticket_triage import activities
from ticket_triage.activities import (
    classify_ticket,
    close_openai_client,
    draft_reply,
    lookup_account,
)
from ticket_triage.workflows import TASK_QUEUE, TicketTriageWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--replay-stress",
        action="store_true",
        help="Disable the workflow cache so every workflow task replays the "
        "workflow from the start of history. Traces must look identical.",
    )
    parser.add_argument(
        "--fail-first-attempt",
        action="store_true",
        help="Fail classify_ticket's first attempt: one RunActivity span per attempt",
    )
    parser.add_argument(
        "--slow-classify",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Heartbeat for SECONDS in classify_ticket first, so you can kill "
        "the worker mid-attempt and watch the retry.",
    )
    args = parser.parse_args()
    activities.FAIL_FIRST_ATTEMPT = args.fail_first_attempt
    activities.SLOW_CLASSIFY_SECONDS = args.slow_classify

    # @@@SNIPSTART python-arize-tracing-worker
    setup_tracing("ticket-triage-worker")
    # Every OpenAI call made from an activity emits an OpenInference LLM span.
    OpenAIInstrumentor().instrument()

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    # add_temporal_spans=True emits spans for Temporal operations (StartWorkflow,
    # RunWorkflow, RunActivity, HandleUpdate, ...) besides propagating context.
    config["plugins"] = [OpenTelemetryPlugin(add_temporal_spans=True)]
    client = await Client.connect(**config)

    worker = Worker(  # workers inherit the client's plugins
        client,
        task_queue=TASK_QUEUE,
        workflows=[TicketTriageWorkflow],
        activities=[classify_ticket, lookup_account, draft_reply],
        max_cached_workflows=0 if args.replay_stress else 1000,
    )
    # @@@SNIPEND

    mode = "replay-stress (workflow cache disabled)" if args.replay_stress else "normal"
    print(f"Worker started (mode={mode}), ctrl+c to exit")
    try:
        await worker.run()
    finally:
        await close_openai_client()
        force_flush()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # the finally block in main() has already flushed the spans
