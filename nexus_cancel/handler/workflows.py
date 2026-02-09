"""
This workflow is started by the hello Nexus operation.
It demonstrates how to handle cancellation from the caller workflow.
"""

import asyncio

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from hello_nexus.service import MyInput, MyOutput


@workflow.defn
class HelloHandlerWorkflow:
    """
    A workflow that handles the hello operation and responds to cancellation.

    This workflow simulates work by sleeping for a random duration, then handles
    cancellation gracefully if requested.
    """

    @workflow.run
    async def run(self, input: MyInput) -> MyOutput:
        try:
            # Sleep for a random duration to simulate some work (0-5 seconds)
            random_seconds = workflow.random().randint(0, 5)
            workflow.logger.info(f"Working for {random_seconds} seconds...")
            await asyncio.sleep(random_seconds)

            # Return the greeting message
            return MyOutput(message=f"Hello {input.name} 👋")

        except asyncio.CancelledError:
            # Simulate some cleanup work after cancellation is requested
            # Use a shield to prevent this cleanup from being cancelled
            workflow.logger.info("Received cancellation request, performing cleanup...")

            try:
                cleanup_seconds = workflow.random().randint(0, 5)
                # Shield this sleep from cancellation to simulate cleanup work
                await asyncio.shield(asyncio.sleep(cleanup_seconds))
                workflow.logger.info("HelloHandlerWorkflow was cancelled successfully.")
            except asyncio.CancelledError:
                # Even if shield is cancelled, log completion
                workflow.logger.info("HelloHandlerWorkflow was cancelled successfully.")

            # Re-raise the cancellation
            raise
