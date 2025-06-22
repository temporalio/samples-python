"""
Starter for the OpenAI Agents Expense Processing Sample.

This script starts expense workflows with AI agent processing.
"""

import asyncio
import uuid
from datetime import date, datetime
from decimal import Decimal

from temporalio.client import Client

from openai_agents_expense import TASK_QUEUE, WORKFLOW_ID_PREFIX
from openai_agents_expense.models import ExpenseReport
from openai_agents_expense.workflows.expense_workflow import ExpenseWorkflow


async def main():
    """Start an expense workflow with AI processing."""
    print("OpenAI Agents Expense Processing Sample - Starter")
    print("=" * 50)
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
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
    
    print("\nSelect an expense to process (1-3), or press Enter for all:")
    choice = input().strip()
    
    expenses_to_process = []
    if choice == "":
        expenses_to_process = sample_expenses
        print("Processing all sample expenses...")
    elif choice in ["1", "2", "3"]:
        expenses_to_process = [sample_expenses[int(choice) - 1]]
        print(f"Processing expense {choice}...")
    else:
        print("Invalid choice. Processing first expense...")
        expenses_to_process = [sample_expenses[0]]
    
    # Process each selected expense
    for expense in expenses_to_process:
        print(f"\nStarting workflow for expense: {expense.expense_id}")
        print(f"Description: {expense.description}")
        print(f"Vendor: {expense.vendor}")
        print(f"Amount: ${expense.amount}")
        
        # Create workflow ID
        workflow_id = f"{WORKFLOW_ID_PREFIX}-{expense.expense_id}"
        
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
            
            # Option to wait for completion
            if len(expenses_to_process) == 1:
                print("\nWait for completion? (y/n):")
                wait = input().strip().lower()
                
                if wait == "y":
                    print("Waiting for workflow completion...")
                    try:
                        result = await handle.result()
                        print(f"Workflow completed with result: {result}")
                        
                        # Get final status
                        status = await handle.query(ExpenseWorkflow.get_status)
                        print(f"\nFinal Status: {status.current_status}")
                        
                        # Get processing result if available
                        try:
                            processing_result = await handle.query(ExpenseWorkflow.get_processing_result)
                            if processing_result:
                                print(f"Decision: {processing_result.final_decision.decision}")
                                print(f"Response: {processing_result.expense_response.message}")
                        except:
                            pass
                            
                    except Exception as e:
                        print(f"Workflow failed: {e}")
                        
        except Exception as e:
            print(f"Failed to start workflow: {e}")
    
    print("\n" + "=" * 50)
    print("Expense workflows started!")
    print("Monitor progress:")
    print("1. Temporal Web UI: http://localhost:8233")
    print("2. Expense UI (for human review): http://localhost:8099/list")
    print("\nNote: Make sure the worker is running to process these workflows.")


if __name__ == "__main__":
    asyncio.run(main()) 