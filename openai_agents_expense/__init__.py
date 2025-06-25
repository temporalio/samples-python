"""
OpenAI Agents Expense Processing Sample

This sample demonstrates AI-enhanced expense processing using OpenAI Agents SDK with Temporal workflows.
It extends the basic expense sample with multi-agent orchestration, fraud detection, and robust guardrails.
"""


from .models import ExpenseProcessingData, ExpenseReport, ExpenseStatus

# Configuration constants
EXPENSE_SERVER_HOST_PORT = "http://localhost:8099"
TASK_QUEUE = "openai-agents-expense-task-queue"
WORKFLOW_ID_PREFIX = "openai-agents-expense-workflow"

# Export main classes and functions
__all__ = [
    "ExpenseReport",
    "ExpenseProcessingData",
    "ExpenseStatus",
    "EXPENSE_SERVER_HOST_PORT",
    "TASK_QUEUE",
    "WORKFLOW_ID_PREFIX",
]
