"""
Starter for the OpenAI Agents Expense Processing Sample.

This script starts expense workflows with AI agent processing.

Usage:
  python starter.py                    # Process expense 1, wait for completion (default behavior)
  python starter.py -e menu           # Show interactive menu, wait for completion
  python starter.py -e 2              # Process expense 2, wait for completion
  python starter.py -e all             # Process all expenses, wait for completion
  python starter.py -e 1 --no-wait    # Process expense 1, don't wait for completion
"""

import argparse
import asyncio
import time
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
  %(prog)s                    # Process expense 1, wait for completion (default)
  %(prog)s -e menu           # Show interactive menu, wait for completion
  %(prog)s -e 2              # Process expense 2, wait for completion
  %(prog)s -e all             # Process all expenses, wait for completion
  %(prog)s -e 1 --no-wait    # Process expense 1, don't wait for completion
        """,
    )

    parser.add_argument(
        "-e",
        "--expense",
        choices=["1", "2", "3", "all", "menu"],
        default="1",
        help="Which expense to process: 1, 2, 3, 'all', or 'menu' for interactive selection (default: 1)",
    )

    parser.add_argument(
        "-w",
        "--wait",
        action="store_true",
        default=True,
        help="Wait for workflow completion (default: True)",
    )

    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for workflow completion (overrides --wait)",
    )

    return parser.parse_args()


def format_expense_details(expense: ExpenseReport) -> str:
    """Format expense details for display."""
    lines = [
        f"┌─── Expense Report: {expense.expense_id} ───",
        f"│ Description: {expense.description}",
        f"│ Amount:      ${expense.amount}",
        f"│ Vendor:      {expense.vendor}",
        f"│ Department:  {expense.department}",
        f"│ Employee:    {expense.employee_id}",
        f"│ Date:        {expense.expense_date}",
        f"│ Receipt:     {'✓ Provided' if expense.receipt_provided else '✗ Missing'}",
    ]

    if expense.client_name:
        lines.append(f"│ Client:      {expense.client_name}")

    if expense.business_justification:
        lines.append(f"│ Justification: {expense.business_justification}")

    if expense.is_international_travel:
        lines.append(f"│ Travel:      🌍 International")

    lines.append("└" + "─" * (len(lines[0]) - 1))

    return "\n".join(lines)


def print_section_header(title: str):
    """Print a nicely formatted section header."""
    print(f"\n{title}")
    print("─" * len(title))


def show_expense_menu(sample_expenses: list) -> str:
    """Show interactive menu for expense selection."""
    print_section_header("Select an Expense to Process")

    for i, expense in enumerate(sample_expenses, 1):
        status_hint = ""
        if i == 1:
            status_hint = " (likely approved)"
        elif i == 2:
            status_hint = " (international - may escalate)"
        elif i == 3:
            status_hint = " (suspicious vendor - may escalate)"

        print(
            f"{i}. {expense.expense_id}: ${expense.amount} - {expense.description}{status_hint}"
        )

    print("4. Process all expenses")
    print()

    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ["1", "2", "3"]:
                return choice
            elif choice == "4":
                return "all"
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            exit(0)


def format_result_with_decision(result: str) -> tuple[str, str]:
    """Analyze result and return decision type and formatted message."""
    result_lower = result.lower()

    if "approved" in result_lower and "escalat" not in result_lower:
        decision = "✅ APPROVED"
        icon = "✅"
    elif "escalat" in result_lower or "review" in result_lower:
        decision = "🔍 ESCALATED"
        icon = "🔍"
    elif "reject" in result_lower or "denied" in result_lower:
        decision = "❌ REJECTED"
        icon = "❌"
    else:
        decision = "📋 PROCESSED"
        icon = "📋"

    return decision, icon


def print_workflow_result(
    expense_id: str, result: str, elapsed_time: float, status: str | None = None
):
    """Print workflow completion result in a nice format."""
    decision, icon = format_result_with_decision(result)

    print_section_header("Processing Complete")
    print(f"Expense ID: {expense_id}")
    print(f"Decision:   {decision}")
    print(f"Result:     {result}")
    print(f"Duration:   {elapsed_time:.1f} seconds")
    if status:
        print(f"Status:     {status}")
    print(f"{icon} Processing completed successfully!")


async def main():
    """Start an expense workflow with AI processing."""
    args = parse_args()

    print("🏢 OpenAI Agents Expense Processing Sample")
    print("=" * 50)

    # Connect to Temporal server with OpenAI agents data converter
    client = await Client.connect(
        "localhost:7233", data_converter=open_ai_data_converter
    )

    # Determine wait behavior (default is to wait, unless --no-wait is specified)
    should_wait = args.wait and not args.no_wait

    # Create sample expense reports for demonstration
    sample_expenses = [
        # Happy path - should auto-approve
        ExpenseReport(
            expense_id="EXP-2024-001",
            amount=Decimal("45.00"),
            description="Office supplies for Q4 planning",
            vendor="Staples Inc",
            expense_date=date(2024, 1, 15),
            department="Marketing",
            employee_id="EMP-001",
            receipt_provided=True,
            submission_date=date(2024, 1, 16),
            client_name=None,
            business_justification=None,
            is_international_travel=False,
        ),
        # International travel - should escalate
        ExpenseReport(
            expense_id="EXP-2024-002",
            amount=Decimal("400.00"),
            description="Flight to London for client meeting",
            vendor="British Airways",
            expense_date=date(2024, 1, 20),
            department="Sales",
            employee_id="EMP-002",
            receipt_provided=True,
            submission_date=date(2024, 1, 21),
            client_name="Global Tech Partners UK",
            business_justification="Quarterly business review meeting with key client",
            is_international_travel=True,
        ),
        # Suspicious vendor - should escalate
        ExpenseReport(
            expense_id="EXP-2024-003",
            amount=Decimal("200.00"),
            description="Team dinner after project completion",
            vendor="Joe's Totally Legit Restaurant LLC",
            expense_date=date(2024, 1, 8),
            department="Engineering",
            employee_id="EMP-003",
            receipt_provided=True,
            submission_date=date(2024, 1, 9),
            client_name=None,
            business_justification="Team celebration dinner following successful product launch",
            is_international_travel=False,
        ),
    ]

    # Determine which expense(s) to process
    if args.expense == "menu":
        # User requested interactive menu
        selected_expense = show_expense_menu(sample_expenses)
    else:
        selected_expense = args.expense

    # Process expenses based on selection
    expenses_to_process = []
    if selected_expense == "all":
        print_section_header("Available Sample Expenses")
        for i, expense in enumerate(sample_expenses, 1):
            status_hint = ""
            if i == 1:
                status_hint = " (likely approved)"
            elif i == 2:
                status_hint = " (international - may escalate)"
            elif i == 3:
                status_hint = " (suspicious vendor - may escalate)"
            print(
                f"{i}. {expense.expense_id}: ${expense.amount} - {expense.description}{status_hint}"
            )
        print("\nProcessing all sample expenses...")
        expenses_to_process = sample_expenses
    elif selected_expense in ["1", "2", "3"]:
        expense_num = int(selected_expense)
        print(f"Processing expense #{expense_num}...")
        expenses_to_process = [sample_expenses[expense_num - 1]]
    else:
        # Fallback
        expenses_to_process = [sample_expenses[0]]

    # Process each selected expense
    processed_count = 0
    total_amount = Decimal("0.00")
    processing_results: list[dict[str, object]] = []

    for expense in expenses_to_process:
        print_section_header(f"Submitting Expense Report")
        print(format_expense_details(expense))

        # Create workflow ID with UUID for uniqueness
        unique_id = str(uuid.uuid4())
        workflow_id = f"{WORKFLOW_ID_PREFIX}-{expense.expense_id}-{unique_id}"

        expense_copy = expense.model_copy()
        expense_copy.expense_id = f"{expense_copy.expense_id}-{unique_id}"

        try:
            # Start the workflow
            start_time = time.time()
            handle = await client.start_workflow(
                ExpenseWorkflow.run,
                expense_copy,
                id=workflow_id,
                task_queue=TASK_QUEUE,
            )

            print(f"\n🚀 Workflow started successfully!")
            print(f"Workflow ID: {workflow_id}")
            print(f"Started at:  {datetime.now().strftime('%H:%M:%S')}")

            # Show monitoring options right after submission
            print(f"\n📊 Monitor Progress:")
            print(
                f"   • Temporal Web UI: http://localhost:8233/namespaces/default/workflows/{workflow_id}"
            )
            print(f"   • Expense Review UI: http://localhost:8099/list")

            if should_wait:
                print("\n⏳ Processing expense through AI agents...")

                try:
                    # Query the workflow status
                    try:
                        status = await handle.query(ExpenseWorkflow.get_status)
                        print(f"Current status: {status.current_status}")
                    except Exception as e:
                        print(f"Note: Could not query status - {e}")

                    # Wait for completion
                    result = await handle.result()
                    elapsed_time = time.time() - start_time

                    print_workflow_result(expense.expense_id, result, elapsed_time)
                    processed_count += 1
                    total_amount += expense.amount

                    decision, _ = format_result_with_decision(result)
                    processing_results.append(
                        {
                            "expense_id": expense.expense_id,
                            "amount": expense.amount,
                            "decision": decision,
                            "duration": elapsed_time,
                        }
                    )

                except Exception as e:
                    print(f"❌ Workflow failed: {e}")
            else:
                print("\n📋 Workflow submitted and running in background")

        except Exception as e:
            print(f"❌ Failed to start workflow: {e}")

    # Enhanced final summary
    print("\n" + "=" * 50)
    if should_wait and processed_count > 0:
        print(f"✅ Successfully processed {processed_count} expense report(s)!")
        print(f"💰 Total amount processed: ${total_amount}")

        if len(processing_results) > 1:
            print_section_header("Processing Summary")
            for proc_result in processing_results:
                expense_id = str(proc_result.get("expense_id", "Unknown"))
                decision = str(proc_result.get("decision", "Unknown"))
                amount = proc_result.get("amount", 0)
                duration = proc_result.get("duration", 0.0)
                print(f"   {expense_id}: {decision} (${amount}, {duration:.1f}s)")

        # Show average processing time
        if processing_results:
            durations = []
            for r in processing_results:
                duration_val = r.get("duration", 0.0)
                if isinstance(duration_val, (int, float)) and duration_val is not None:
                    durations.append(float(duration_val))
            avg_time = sum(durations) / len(durations) if durations else 0.0
            print(f"⏱️  Average processing time: {avg_time:.1f} seconds")

    elif should_wait:
        print("⚠️  No expenses were successfully processed")
    else:
        print(f"📤 {len(expenses_to_process)} expense workflow(s) submitted!")
        total_submitted = sum(expense.amount for expense in expenses_to_process)
        print(f"💰 Total amount submitted: ${total_submitted}")

    print("\n⚙️  Note: Ensure the worker is running to process workflows")


if __name__ == "__main__":
    asyncio.run(main())
