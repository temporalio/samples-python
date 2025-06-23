"""
Starter for the OpenAI Agents Expense Processing Sample.

This script starts expense workflows with AI agent processing.

Usage:
  python starter.py                    # Process first expense, don't wait
  python starter.py -e 2              # Process expense 2, don't wait  
  python starter.py -e all -w          # Process all expenses and wait for completion
  python starter.py --expense 1 --wait # Process expense 1 and wait for completion
"""

import argparse
import asyncio
import uuid
from datetime import date, datetime
from decimal import Decimal

from temporalio.client import Client
from temporalio.contrib.openai_agents.open_ai_data_converter import (
    open_ai_data_converter,
)

from openai_agents_expense import TASK_QUEUE, WORKFLOW_ID_PREFIX
from openai_agents_expense.models import ExpenseReport
from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Start OpenAI Agents Expense Processing workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Process first expense, don't wait
  %(prog)s -e 2              # Process expense 2, don't wait  
  %(prog)s -e all -w          # Process all expenses and wait for completion
  %(prog)s --expense 1 --wait # Process expense 1 and wait for completion
        """
    )
    
    parser.add_argument(
        "-e", "--expense",
        choices=["1", "2", "3", "all"],
        default="1",
        help="Which expense to process: 1, 2, 3, or 'all' (default: 1)"
    )
    
    parser.add_argument(
        "-w", "--wait",
        action="store_true",
        help="Wait for workflow completion and show results"
    )
    
    return parser.parse_args()


async def main():
    """Start an expense workflow with AI processing."""
    args = parse_args()
    
    print("OpenAI Agents Expense Processing Sample - Starter")
    print("=" * 50)
    
    # Connect to Temporal server with OpenAI agents data converter
    client = await Client.connect(
        "localhost:7233",
        data_converter=open_ai_data_converter
    )
    
    # Create sample expense reports for demonstration
    sample_expenses = [
        # Happy path - should auto-approve
        ExpenseReport(
            expense_id="EXP-2024-001",
            amount=Decimal("45.00"),
            description="Office supplies for Q4 planning",
            vendor="Staples Inc",
            date=date(2024, 1, 15),
            department="Marketing",
            employee_id="EMP-001",
            receipt_provided=True,
            submission_date=date(2024, 1, 16),
            client_name=None,
            business_justification=None,
            is_international_travel=False
        ),
        
        # International travel - should escalate
        ExpenseReport(
            expense_id="EXP-2024-002",
            amount=Decimal("400.00"),
            description="Flight to London for client meeting",
            vendor="British Airways",
            date=date(2024, 1, 20),
            department="Sales",
            employee_id="EMP-002",
            receipt_provided=True,
            submission_date=date(2024, 1, 21),
            client_name="Global Tech Partners UK",
            business_justification="Quarterly business review meeting with key client",
            is_international_travel=True
        ),
        
        # Suspicious vendor - should escalate
        ExpenseReport(
            expense_id="EXP-2024-003",
            amount=Decimal("200.00"),
            description="Team dinner after project completion",
            vendor="Joe's Totally Legit Restaurant LLC",
            date=date(2024, 1, 8),
            department="Engineering",
            employee_id="EMP-003",
            receipt_provided=True,
            submission_date=date(2024, 1, 9),
            client_name=None,
            business_justification="Team celebration dinner following successful product launch",
            is_international_travel=False
        )
    ]
    
    print("Available sample expenses:")
    for i, expense in enumerate(sample_expenses, 1):
        print(f"{i}. {expense.expense_id}: ${expense.amount} - {expense.description}")
    
    # Process expenses based on command line argument
    expenses_to_process = []
    if args.expense == "all":
        expenses_to_process = sample_expenses
        print(f"\nProcessing all sample expenses...")
    elif args.expense in ["1", "2", "3"]:
        expenses_to_process = [sample_expenses[int(args.expense) - 1]]
        print(f"\nProcessing expense {args.expense}...")
    else:
        expenses_to_process = [sample_expenses[0]]
        print(f"\nProcessing first expense (default)...")
    
    # Process each selected expense
    for expense in expenses_to_process:
        print(f"\nStarting workflow for expense: {expense.expense_id}")
        print(f"Description: {expense.description}")
        print(f"Vendor: {expense.vendor}")
        print(f"Amount: ${expense.amount}")
        
        # Create workflow ID with UUID for uniqueness
        unique_id = str(uuid.uuid4())
        workflow_id = f"{WORKFLOW_ID_PREFIX}-{expense.expense_id}-{unique_id}"
        
        try:
            # Start the workflow
            handle = await client.start_workflow(
                ExpenseWorkflow.run,
                expense,
                id=workflow_id,
                task_queue=TASK_QUEUE,
            )
            
            print(f"Workflow started: {workflow_id}")
            print(f"You can track progress at: http://localhost:8233/namespaces/default/workflows/{workflow_id}")
            
            # Wait for completion if requested
            if args.wait:
                print("Waiting for workflow completion...")
                try:
                    # Query the workflow BEFORE waiting for completion
                    try:
                        status = await handle.query(ExpenseWorkflow.get_status)
                        print(f"Current Status: {status.current_status}")
                    except Exception as e:
                        print(f"Could not get status: {e}")
                    
                    # Now wait for completion
                    result = await handle.result()
                    print(f"Workflow completed with result: {result}")
                    
                    # Try to get processing result, but don't query after completion
                    print("Workflow processing completed successfully!")
                        
                except Exception as e:
                    print(f"Workflow failed: {e}")
            else:
                print("Use --wait/-w flag to wait for completion and see results")
                        
        except Exception as e:
            print(f"Failed to start workflow: {e}")
    
    print("\n" + "=" * 50)
    print("Expense workflows started!")
    print("Monitor progress:")
    print("1. Temporal Web UI: http://localhost:8233")
    print("2. Expense UI (for human review): http://localhost:8099/list")
    print(f"\nNote: Make sure the worker is running to process these workflows.")
    if not args.wait:
        print("Tip: Use --wait/-w flag to automatically wait for completion and see results")


if __name__ == "__main__":
    asyncio.run(main()) 