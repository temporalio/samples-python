"""
Worker for the OpenAI Agents Expense Processing Sample.

This worker runs the expense workflow with AI agents and web search activities.
"""

import asyncio
import concurrent.futures
import logging
import sys
from datetime import timedelta

from temporalio.client import Client
from temporalio.contrib.openai_agents.invoke_model_activity import ModelActivity
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)
from temporalio.contrib.openai_agents.temporal_openai_agents import (
    set_open_ai_agent_temporal_overrides,
)
from temporalio.worker import Worker

# Import workflow and activities
from openai_agents_expense import TASK_QUEUE

# Import the expense activities from this package (self-contained)
from openai_agents_expense.activities import (
    create_expense_activity,
    payment_activity,
    wait_for_decision_activity,
)
from openai_agents_expense.activities.expense_activities import update_expense_activity
from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow


async def main():
    """Main worker function with proper configuration and error handling."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Set Temporal logging level (simple approach)
    temporal_log_level = logging.DEBUG
    temporal_logger = logging.getLogger("temporalio")
    temporal_logger.setLevel(temporal_log_level)

    logger.info("Starting OpenAI Agents Expense worker...")

    try:
        with set_open_ai_agent_temporal_overrides(
            start_to_close_timeout=timedelta(seconds=60),
        ):
            # Connect to Temporal server with OpenAI data converter
            client = await Client.connect(
                "localhost:7233", data_converter=open_ai_data_converter
            )
            logger.info("Connected to Temporal server with OpenAI data converter")

            # Initialize ModelActivity for LLM invocation (required by AI agents)
            model_activity = ModelActivity()
            logger.info("ModelActivity initialized for LLM invocation")

            # Create worker with workflows and activities
            worker = Worker(
                client,
                task_queue=TASK_QUEUE,
                workflows=[ExpenseWorkflow],
                activities=[
                    # Core LLM invocation activity (required by AI agents)
                    model_activity.invoke_model_activity,
                    # UI and payment integration activities
                    create_expense_activity,
                    wait_for_decision_activity,
                    payment_activity,
                    update_expense_activity,
                ],
                # Configure workflow cache for better performance
                max_cached_workflows=100,
                # Use thread pool for activities that may be CPU-intensive
                activity_executor=concurrent.futures.ThreadPoolExecutor(
                    max_workers=100
                ),
            )

            logger.info("Worker configuration:")
            logger.info(f"  - Task Queue: {TASK_QUEUE}")
            # TODO avoid hardcoding numbers in the output below
            logger.info("\nPress Ctrl+C to stop the worker")

            # Run the worker
            await worker.run()

    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
