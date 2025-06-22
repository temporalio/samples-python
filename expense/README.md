# Expense

This sample workflow processes an expense request. It demonstrates human-in-the loop processing and asynchronous activity completion.

## Overview

This sample demonstrates the following workflow:

1. **Create Expense**: The workflow executes the `create_expense_activity` to initialize a new expense report in the external system.

2. **Wait for Decision**: The workflow calls `wait_for_decision_activity`, which demonstrates asynchronous activity completion. The activity registers itself for external completion using its task token, then calls `activity.raise_complete_async()` to signal that it will complete later without blocking the worker.

3. **Async Completion**: When a human approves or rejects the expense, an external process uses the stored task token to call `workflow_client.get_async_activity_handle(task_token).complete()`, notifying Temporal that the waiting activity has finished and providing the decision result.

4. **Process Payment**: Once the workflow receives the approval decision, it executes the `payment_activity` to complete the simulated expense processing.

This pattern enables human-in-the-loop workflows where activities can wait as long as necessary for external decisions without consuming worker resources or timing out.

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
  uv run -m expense.starter
  ```
* When you see the console print out that the expense is created, go to [localhost:8099/list](http://localhost:8099/list) to approve the expense.
* You should see the workflow complete after you approve the expense. You can also reject the expense.

## Running Tests

```bash
# Run all tests
uv run pytest expense/test_workflow.py -v

# Run a specific test
uv run pytest expense/test_workflow.py::TestSampleExpenseWorkflow::test_workflow_with_mock_activities -v
```

## Key Concepts Demonstrated

* **Human-in-the-Loop Workflows**: Long-running workflows that wait for human interaction
* **Async Activity Completion**: Using `activity.raise_complete_async()` to indicate an activity will complete asynchronously, then calling `complete()` on a handle to the async activity.
* **External System Integration**: Communication between workflows and external systems via web services.

## Troubleshooting

If you see the workflow failed, the cause may be a port conflict. You can try to change to a different port number in `__init__.py`. Then rerun everything.

## Files

* `workflow.py` - The main expense processing workflow
* `activities.py` - Three activities: create expense, wait for decision, process payment
* `ui.py` - A demonstration expense approval system web UI
* `worker.py` - Worker to run workflows
* `starter.py` - Client to start workflow executions by submitting an expense report