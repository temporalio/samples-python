"""Worker for the ticket triage agents sample."""

import argparse
import asyncio
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig
from temporalio.worker import Worker

from arize_tracing.telemetry import (
    force_flush,
    quiet_otel_context_detach_errors,
    setup_tracing,
)
from arize_tracing.ticket_triage.activities import lookup_account
from arize_tracing.ticket_triage_agents.plugin import TASK_QUEUE, agents_plugin
from arize_tracing.ticket_triage_agents.workflows import TicketTriageAgentsWorkflow


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--replay-stress",
        action="store_true",
        help="Disable the workflow cache so every workflow task replays the "
        "workflow (and the agent loop) from the start of history. Traces in "
        "Arize must look identical with or without this flag.",
    )
    args = parser.parse_args()

    # @@@SNIPSTART python-arize-tracing-agents-worker
    # The tracer provider must exist before the plugin is constructed.
    setup_tracing("ticket-triage-agents-worker")
    quiet_otel_context_detach_errors()

    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config, plugins=[agents_plugin()])

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[TicketTriageAgentsWorkflow],
        # The plugin registers the model-call activity itself.
        activities=[lookup_account],
        max_cached_workflows=0 if args.replay_stress else 1000,
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
