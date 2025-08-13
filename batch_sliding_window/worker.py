#!/usr/bin/env python3
"""Worker for the batch sliding window sample."""

import asyncio
import logging

from temporalio import worker
from temporalio.client import Client
from temporalio.envconfig import ClientConfigProfile

from batch_sliding_window.batch_workflow import ProcessBatchWorkflow
from batch_sliding_window.record_loader_activity import RecordLoader
from batch_sliding_window.record_processor_workflow import RecordProcessorWorkflow
from batch_sliding_window.sliding_window_workflow import SlidingWindowWorkflow


async def main():
    """Run the worker that registers all workflows and activities."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create client
    config = ClientConfigProfile.load()
    config["address"] = "localhost:7233"
    client = await Client.connect(**config.to_client_connect_config())

    # Create RecordLoader activity with sample data
    record_loader = RecordLoader(record_count=90)

    # Create worker
    temporal_worker = worker.Worker(
        client,
        task_queue="batch_sliding_window_task_queue",
        workflows=[
            ProcessBatchWorkflow,
            SlidingWindowWorkflow,
            RecordProcessorWorkflow,
        ],
        activities=[
            record_loader.get_record_count,
            record_loader.get_records,
        ],
    )

    print("Starting worker...")
    # Run the worker
    await temporal_worker.run()


if __name__ == "__main__":
    asyncio.run(main())
