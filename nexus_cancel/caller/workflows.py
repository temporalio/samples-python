"""
This workflow demonstrates how to cancel Nexus operations using cancellation scopes.

This sample shows how to use the WAIT_REQUESTED cancellation type, which allows
the caller to return after the handler workflow has received the cancellation request,
but does not wait for the handler workflow to finish processing the cancellation.
"""

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import CancelledError, NexusOperationError

with workflow.unsafe.imports_passed_through():
    from hello_nexus.service import MyInput, MyNexusService, MyOutput

NEXUS_ENDPOINT = "my-nexus-endpoint-name"


@workflow.defn
class HelloCallerWorkflow:
    """
    A workflow that calls multiple Nexus operations concurrently and cancels them
    after the first one completes.

    This demonstrates the WAIT_REQUESTED cancellation type, which ensures the handler
    receives the cancellation request but doesn't wait for it to complete.
    """

    def __init__(self):
        self.nexus_client = workflow.create_nexus_client(
            service=MyNexusService,
            endpoint=NEXUS_ENDPOINT,
            # Set the cancellation type to WAIT_REQUESTED. This means that the caller
            # will wait for the cancellation request to be received by the handler before
            # proceeding with the cancellation.
            #
            # By default, the caller would wait until the operation is completed.
            operation_options=workflow.NexusOperationOptions(
                schedule_to_close_timeout=timedelta(seconds=10),
                cancellation_type=workflow.NexusOperationCancellationType.WAIT_REQUESTED,
            ),
        )

    @workflow.run
    async def run(self, message: str) -> str:
        """
        Execute multiple Nexus operations concurrently and return the first result.

        Args:
            message: The message to pass to the Nexus operations

        Returns:
            The result from the first completed operation
        """
        # Names to call the operation with concurrently
        names = ["Nexus-1", "Nexus-2", "Nexus-3", "Nexus-4", "Nexus-5"]

        # Create a list to store operation tasks
        tasks = []

        # Create our cancellation scope. Within this scope we call the nexus operation
        # asynchronously for each name.
        async def start_operations():
            for name in names:
                # Start each operation asynchronously
                handle = await self.nexus_client.start_operation(
                    MyNexusService.my_workflow_run_operation,
                    MyInput(name),
                )
                # Create a task that waits for the operation result
                tasks.append(asyncio.create_task(handle))

        # Execute all nexus operations within a try block so we can cancel them
        try:
            # Start all operations
            await start_operations()

            # Wait for the first operation to complete
            workflow.logger.info(f"Started {len(tasks)} operations, waiting for first to complete...")
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # Get the result from the first completed operation
            result = await done.pop()
            workflow.logger.info(f"First operation completed with: {result.message}")

            # Cancel all remaining operations
            workflow.logger.info(f"Cancelling {len(pending)} remaining operations...")
            for task in pending:
                task.cancel()

            # Wait for all operations to receive cancellation requests before proceeding
            # Note: Once the workflow completes any pending cancellation requests are
            # dropped by the server. In general, it is a good practice to wait for all
            # cancellation requests to be processed before completing the workflow.
            for task in pending:
                try:
                    await task
                except (NexusOperationError, CancelledError) as e:
                    # If the operation was cancelled, we can ignore the failure
                    if isinstance(e, NexusOperationError) and isinstance(
                        e.__cause__, CancelledError
                    ):
                        workflow.logger.info("Operation was cancelled")
                        continue
                    if isinstance(e, CancelledError):
                        workflow.logger.info("Operation was cancelled")
                        continue
                    raise e

            return result.message

        except Exception as e:
            workflow.logger.error(f"Error during operation execution: {e}")
            raise
