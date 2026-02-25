"""
Caller workflow that demonstrates Nexus operation cancellation.

Fans out 5 concurrent Nexus hello operations (one per language), takes the first
result, and cancels the rest using WAIT_REQUESTED cancellation semantics.
"""

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import CancelledError, NexusOperationError

with workflow.unsafe.imports_passed_through():
    from nexus_cancel.service import HelloInput, Language, NexusService

NEXUS_ENDPOINT = "nexus-cancel-endpoint"


@workflow.defn
class HelloCallerWorkflow:
    def __init__(self) -> None:
        self.nexus_client = workflow.create_nexus_client(
            service=NexusService,
            endpoint=NEXUS_ENDPOINT,
        )

    @workflow.run
    async def run(self, message: str) -> str:
        # Fan out 5 concurrent Nexus calls, one per language.
        # Each task starts and awaits its own operation so all race concurrently.
        async def run_operation(language: Language):
            handle = await self.nexus_client.start_operation(
                NexusService.hello,
                HelloInput(name=message, language=language),
                schedule_to_close_timeout=timedelta(seconds=10),
                cancellation_type=workflow.NexusOperationCancellationType.WAIT_REQUESTED,
            )
            return await handle

        tasks = [asyncio.create_task(run_operation(lang)) for lang in Language]

        # Wait for the first operation to complete
        workflow.logger.info(
            f"Started {len(tasks)} operations, waiting for first to complete..."
        )
        done, pending = await workflow.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Get the result from the first completed operation
        result = await done.pop()
        workflow.logger.info(f"First operation completed with: {result.message}")

        # Cancel all remaining operations
        workflow.logger.info(f"Cancelling {len(pending)} remaining operations...")
        for task in pending:
            task.cancel()

        # Wait for all cancellations to be acknowledged.
        # If the workflow completes before cancellation requests are delivered,
        # the server drops them. Waiting ensures all handlers receive the
        # cancellation.
        for task in pending:
            try:
                await task
            except (NexusOperationError, CancelledError):
                # Expected: the operation was cancelled
                workflow.logger.info("Operation was cancelled")

        return result.message
