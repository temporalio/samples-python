#!/usr/bin/env python3
"""Starter for the batch sliding window sample."""

import asyncio
import datetime
import logging

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from batch_sliding_window.batch_workflow import (
    ProcessBatchWorkflow,
    ProcessBatchWorkflowInput,
)


async def main():
    """Start the ProcessBatchWorkflow."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create client
    config = ClientConfig.load_client_connect_config()
    config.setdefault("target_host", "localhost:7233")
    client = await Client.connect(**config)

    # Create unique workflow ID with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    workflow_id = f"batch_sliding_window_example_{timestamp}"

    # Define workflow input
    workflow_input = ProcessBatchWorkflowInput(
        page_size=5,
        sliding_window_size=10,
        partitions=3,
    )

    print(f"Starting workflow with ID: {workflow_id}")
    print(f"Input: {workflow_input}")

    # Start workflow
    handle = await client.start_workflow(
        ProcessBatchWorkflow.run,
        workflow_input,
        id=workflow_id,
        task_queue="batch_sliding_window_task_queue",
    )

    print(f"Workflow started with ID: {handle.id}")
    print(f"Waiting for workflow to complete...")

    # Wait for result
    try:
        result = await handle.result()
        print(f"Workflow completed successfully!")
        print(f"Total records processed: {result}")
    except Exception as e:
        print(f"Workflow failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
