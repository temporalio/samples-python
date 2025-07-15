# Expense

This sample workflow processes an expense request. It demonstrates human-in-the loop processing using Temporal's signal mechanism.

## Overview

This sample demonstrates the following workflow:

1. **Create Expense**: The workflow executes the `create_expense_activity` to initialize a new expense report in the external system.

2. **Register for Decision**: The workflow calls `register_for_decision_activity`, which registers the workflow with the external UI system so it can receive signals when decisions are made.

3. **Wait for Signal**: The workflow uses `workflow.wait_condition()` to wait for an external signal containing the approval/rejection decision.

4. **Signal-Based Completion**: When a human approves or rejects the expense, the external UI system sends a signal to the workflow using `workflow_handle.signal()`, providing the decision result.

5. **Process Payment**: Once the workflow receives the approval decision via signal, it executes the `payment_activity` to complete the simulated expense processing.

This pattern enables human-in-the-loop workflows where workflows can wait as long as necessary for external decisions using Temporal's durable signal mechanism.

## Steps To Run Sample

* You need a Temporal service running. See the main [README.md](../README.md) for more details.
* Start the sample expense system UI:
  ```bash
  uv run -m expense.ui
  ```
* Start workflow and activity workers:
  ```bash
  uv run -m expense.worker
  ```
* Start expense workflow execution:
  ```bash
  # Start workflow and return immediately (default)
  uv run -m expense.starter

  # Start workflow and wait for completion
  uv run -m expense.starter --wait

  # Start workflow with custom expense ID
  uv run -m expense.starter --expense-id "my-expense-123"

  # Start workflow with custom ID and wait for completion
  uv run -m expense.starter --wait --expense-id "my-expense-123"
  ```
* When you see the console print out that the expense is created, go to [localhost:8099/list](http://localhost:8099/list) to approve the expense.
* You should see the workflow complete after you approve the expense. You can also reject the expense.

## Running Tests

```bash
# Run all expense tests
uv run -m pytest tests/expense/ -v

# Run specific test categories
uv run -m pytest tests/expense/test_expense_workflow.py -v  # Workflow tests
uv run -m pytest tests/expense/test_expense_activities.py -v  # Activity tests
uv run -m pytest tests/expense/test_expense_integration.py -v  # Integration tests
uv run -m pytest tests/expense/test_ui.py -v  # UI tests

# Run a specific test
uv run -m pytest tests/expense/test_expense_workflow.py::TestWorkflowPaths::test_workflow_approved_complete_flow -v
```

## Key Concepts Demonstrated

* **Human-in-the-Loop Workflows**: Long-running workflows that wait for human interaction
* **Workflow Signals**: Using `workflow.signal()` and `workflow.wait_condition()` for external communication
* **Signal-Based Completion**: External systems sending signals to workflows for asynchronous decision-making
* **External System Integration**: Communication between workflows and external systems via web services and signals
* **HTTP Client Lifecycle Management**: Proper resource management with worker-scoped HTTP clients

## Troubleshooting

If you see the workflow failed, the cause may be a port conflict. You can try to change to a different port number in `__init__.py`. Then rerun everything.

## Files

* `workflow.py` - The main expense processing workflow with signal handling
* `activities.py` - Three activities: create expense, register for decision, process payment
* `ui.py` - A demonstration expense approval system web UI with signal sending
* `worker.py` - Worker to run workflows and activities with HTTP client lifecycle management
* `starter.py` - Client to start workflow executions with optional completion waiting