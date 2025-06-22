"""
Worker for the OpenAI Agents Expense Processing Sample.

This worker runs the expense workflow with AI agents and web search activities.
"""

import asyncio
import logging

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

# Import workflow and activities
from openai_agents_expense import TASK_QUEUE
from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow
from openai_agents_expense.activities.web_search import web_search_activity

# Also import the original expense activities for human-in-the-loop integration
from expense.activities import (
    create_expense_activity,
    wait_for_decision_activity,
    payment_activity,
)


async def main():
    """Main worker function."""
    logging.basicConfig(level=logging.INFO)
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Create worker with both workflows and activities
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ExpenseWorkflow],
        activities=[
            # OpenAI Agents Expense activities
            web_search_activity,
            # Original expense activities for integration
            create_expense_activity,
            wait_for_decision_activity,
            payment_activity,
        ],
        # Configure workflow cache for better performance
        max_cached_workflows=100,
    )
    
    print(f"Starting OpenAI Agents Expense worker on task queue: {TASK_QUEUE}")
    print("Worker supports:")
    print("  - ExpenseWorkflow (AI-enhanced expense processing)")
    print("  - Web search activity for vendor validation")
    print("  - Original expense activities for human-in-the-loop integration")
    print("\nPress Ctrl+C to stop the worker")
    
    # Run the worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main()) 