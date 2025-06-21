# Expense

This sample workflow processes an expense request. The key part of this sample is to show how to complete an activity asynchronously.

## Sample Description

* Create a new expense report.
* Wait for the expense report to be approved. This could take an arbitrary amount of time. So the activity's `execute` method has to return before it is actually approved. This is done by raising `activity.AsyncActivityCompleteError` so the framework knows the activity is not completed yet.
  * When the expense is approved (or rejected), somewhere in the world needs to be notified, and it will need to call `client.get_async_activity_handle().complete()` to tell Temporal service that the activity is now completed.
  In this sample case, the sample expense system does this job. In real world, you will need to register some listener to the expense system or you will need to have your own polling agent to check for the expense status periodically.
* After the wait activity is completed, it does the payment for the expense (UI step in this sample case).

This sample relies on a sample expense system to work.

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
* If you see the workflow failed, try to change to a different port number in `ui.py` and `activities.py`. Then rerun everything.

## Running Tests

```bash
# Run all tests
uv run pytest expense/test_workflow.py -v

# Run a specific test
uv run pytest expense/test_workflow.py::TestSampleExpenseWorkflow::test_workflow_with_mock_activities -v
```

## Key Concepts Demonstrated

* **Async Activity Completion**: Using `activity.raise_complete_async()` to indicate an activity will complete asynchronously
* **Human-in-the-Loop Workflows**: Long-running workflows that wait for human interaction
* **External System Integration**: HTTP-based communication between activities and external systems
* **Task Tokens**: Using task tokens to complete activities from external systems
* **Web UI Integration**: FastAPI-based expense approval system

## Files

* `workflow.py` - The main expense processing workflow
* `activities.py` - Three activities: create expense, wait for decision, process payment
* `ui.py` - FastAPI-based mock expense system with web UI
* `worker.py` - Worker to run workflows and activities
* `starter.py` - Client to start workflow executions
* `test_workflow.py` - Unit tests with mocked activities 