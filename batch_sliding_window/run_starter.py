#!/usr/bin/env python3
"""Starter for the batch sliding window sample."""

import asyncio
import logging

from temporalio.client import Client

from batch_sliding_window.batch_workflow import ProcessBatchWorkflow, ProcessBatchWorkflowInput


async def main():
    """Start the ProcessBatchWorkflow."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create client
    client = await Client.connect("localhost:7233")

    # Create workflow input
    workflow_input = ProcessBatchWorkflowInput(
        page_size=5,
        sliding_window_size=10,
        partitions=3,
    )

    print(f"Starting workflow with input: {workflow_input}")

    # Start workflow
    handle = await client.start_workflow(
        ProcessBatchWorkflow.run,
        workflow_input,
        id="batch_sliding_window_example",
        task_queue="batch_sliding_window",
    )

    print(f"Started workflow: {handle.id}")

    # Wait for workflow completion
    # This is rarely needed in real use cases as batch workflows are usually long-running
    result = await handle.result()
    print(f"Workflow completed. Total records processed: {result}")


if __name__ == "__main__":
    asyncio.run(main()) 