"""Worker for the ticket triage sample."""

import argparse
import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.opentelemetry import OpenTelemetryPlugin
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from arize_tracing.telemetry import force_flush, instrument_openai, setup_tracing
from arize_tracing.ticket_triage import activities
from arize_tracing.ticket_triage.activities import (
    classify_ticket,
    draft_reply,
    lookup_account,
)
from arize_tracing.ticket_triage.workflows import TicketTriageWorkflow

TASK_QUEUE = "arize-ticket-triage-task-queue"


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--replay-stress",
        action="store_true",
        help="Disable the workflow cache so every workflow task replays the "
        "workflow from the start of history — the harshest test that tracing "
        "emits each span exactly once. Traces in Arize must look identical "
        "with or without this flag.",
    )
    parser.add_argument(
        "--fail-first-attempt",
        action="store_true",
        help="Make classify_ticket fail on its first attempt so the trace shows "
        "one RunActivity span per attempt (the first with an error status).",
    )
    parser.add_argument(
        "--slow-classify",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Make classify_ticket heartbeat for SECONDS before calling the LLM, "
        "so you can kill the worker mid-attempt and watch the retry.",
    )
    args = parser.parse_args()
    activities.FAIL_FIRST_ATTEMPT = args.fail_first_attempt
    activities.SLOW_CLASSIFY_SECONDS = args.slow_classify

    # @@@SNIPSTART python-arize-tracing-worker
    setup_tracing("ticket-triage-worker")
    instrument_openai()

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")

    # add_temporal_spans=True emits spans for Temporal operations (StartWorkflow,
    # RunWorkflow, RunActivity, HandleUpdate, ...) in addition to propagating
    # trace context across the client/workflow/activity boundaries.
    client = await Client.connect(
        **config,
        plugins=[OpenTelemetryPlugin(add_temporal_spans=True)],
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[TicketTriageWorkflow],
        activities=[classify_ticket, lookup_account, draft_reply],
        max_cached_workflows=0 if args.replay_stress else 1000,
        # No plugins here: workers inherit them from the client.
    )
    # @@@SNIPEND

    mode = "replay-stress (workflow cache disabled)" if args.replay_stress else "normal"
    print(f"Worker started (mode={mode}), ctrl+c to exit")
    try:
        await worker.run()
    finally:
        force_flush()


if __name__ == "__main__":
    asyncio.run(main())
