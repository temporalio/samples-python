# Human-in-the-Loop Approval Workflow

A workflow demonstrating human-in-the-loop approval using LangGraph's `interrupt()` function with Temporal signals and queries.

## What This Sample Demonstrates

- **LangGraph interrupt**: Using `interrupt()` to pause graph execution for human input
- **Temporal signals**: Receiving approval/rejection decisions from external systems
- **Temporal queries**: Checking pending approval status and workflow state
- **Timeout handling**: Optional approval deadlines with auto-rejection

## How It Works

1. **process_request**: Validates the request and determines risk level based on amount
2. **request_approval**: Calls `interrupt()` to pause execution and wait for human input
3. **execute_action**: Processes the approved request or handles rejection

The workflow flow:
```
Request → [Process & Assess Risk] → [Interrupt for Approval] → [Execute or Reject] → Result
```

When the graph hits `interrupt()`:
1. Workflow receives `__interrupt__` in the result with approval request details
2. Workflow waits for a signal with human input (with optional timeout)
3. Workflow resumes the graph with `Command(resume=response)`
4. Graph completes with the execute_action node

## Prerequisites

- Temporal server running locally (`temporal server start-dev`)

## Running the Example

First, start the worker:
```bash
uv run python -m langgraph_samples.human_in_loop.approval_workflow.run_worker
```

Then, in a separate terminal, run the workflow:
```bash
uv run python -m langgraph_samples.human_in_loop.approval_workflow.run_workflow
```

## Expected Output

```
============================================================
Example 1: Approving a purchase request
============================================================

Pending approval: {'request_type': 'purchase', 'amount': 500.0, 'risk_level': 'medium', ...}
Workflow status: waiting_for_approval

Sending approval signal...

Result: Successfully processed purchase for $500.00. Approved by manager@example.com: Within budget
Executed: True

============================================================
Example 2: Rejecting a high-risk request
============================================================

Pending approval: {'request_type': 'transfer', 'amount': 50000.0, 'risk_level': 'high', ...}

Sending rejection signal...

Result: Request rejected by compliance@example.com: Amount exceeds single-approval limit
Executed: False
```

## Key APIs Used

- `interrupt(value)`: Pauses graph execution and returns `value` in `__interrupt__`
- `Command(resume=response)`: Resumes graph execution with the given response
- `@workflow.signal`: Receives external input (approval response)
- `@workflow.query`: Exposes workflow state (pending approval, status)
