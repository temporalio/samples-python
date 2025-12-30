# Human-in-the-Loop Approval Workflow (Condition-based)

A workflow demonstrating human-in-the-loop approval using `run_in_workflow=True` with `workflow.wait_condition()` to wait for signals directly in graph nodes.

## What This Sample Demonstrates

- **run_in_workflow=True**: Using this metadata to run graph nodes inside the workflow
- **workflow.instance()**: Accessing the workflow instance from graph nodes
- **Temporal signals**: Receiving approval/rejection decisions directly in graph nodes
- **Temporal queries**: Checking pending approval status and workflow state
- **Notification activity**: Alerting approvers when approval is needed
- **CLI response tool**: Separate script for approvers to respond to requests

## How It Works

1. **process_request**: Validates the request and determines risk level based on amount
2. **request_approval** (`run_in_workflow=True`): Accesses Temporal operations directly:
   - Calls notification activity
   - Waits for approval signal using `workflow.wait_condition()`
3. **execute_action**: Processes the approved request or handles rejection

The workflow flow:
```
Request → [Process & Assess Risk] → [Wait for Signal in Node] → [Execute or Reject] → Result
```

## Comparison with interrupt() Approach

This sample uses `run_in_workflow=True` instead of `interrupt()`:

| Aspect | interrupt() | run_in_workflow=True |
|--------|-------------|---------------------|
| Signal handling | In workflow | In graph node |
| Activity calls | In workflow | In graph node |
| Workflow complexity | More complex | Simpler |
| Graph encapsulation | Logic split | All logic in graph |

Use `run_in_workflow=True` when you want to keep all the waiting and signaling logic within the graph itself.

## Prerequisites

- Temporal server running locally (`temporal server start-dev`)

## Running the Example

**Terminal 1 - Start the worker:**
```bash
uv run langgraph_samples/human_in_the_loop/approval_wait_condition/run_worker.py
```

**Terminal 2 - Start a workflow:**
```bash
uv run langgraph_samples/human_in_the_loop/approval_wait_condition/run_workflow.py
```

The worker will print notification instructions like:
```
*** APPROVAL NEEDED ***
Workflow ID: approval-condition-abc12345
Request: Please approve purchase for $500.00 (Risk: medium)

To respond, run:
  Approve: uv run langgraph_samples/human_in_the_loop/approval_wait_condition/run_respond.py approval-condition-abc12345 --approve --reason 'Your reason'
  Reject:  uv run langgraph_samples/human_in_the_loop/approval_wait_condition/run_respond.py approval-condition-abc12345 --reject --reason 'Your reason'
```

**Terminal 3 - Respond to the approval request:**
```bash
# Check status
uv run langgraph_samples/human_in_the_loop/approval_wait_condition/run_respond.py approval-condition-abc12345 --status

# Approve
uv run langgraph_samples/human_in_the_loop/approval_wait_condition/run_respond.py approval-condition-abc12345 --approve --reason "Within budget"

# Or reject
uv run langgraph_samples/human_in_the_loop/approval_wait_condition/run_respond.py approval-condition-abc12345 --reject --reason "Needs manager approval"
```

## Response Script Options

```
usage: run_respond.py [-h] [--approve] [--reject] [--status] [--reason REASON] [--approver APPROVER] workflow_id

positional arguments:
  workflow_id          The workflow ID to respond to

options:
  --approve            Approve the request
  --reject             Reject the request
  --status             Check workflow status
  --reason REASON      Reason for approval/rejection
  --approver APPROVER  Approver identifier (default: cli-user)
```

## Expected Output

**Workflow starter (Terminal 2):**
```
Starting approval workflow: approval-condition-abc12345
Workflow started. Waiting for result...

To approve/reject, use the run_respond script (see worker output for commands)

============================================================
Result: Successfully processed purchase for $500.00. Approved by cli-user: Within budget
Executed: True
```

## Key APIs Used

- `run_in_workflow=True`: Metadata to run node inside workflow context
- `workflow.instance()`: Get access to the current workflow instance
- `workflow.wait_condition()`: Wait for signal in graph node
- `workflow.execute_activity()`: Call activities from graph node
- `@workflow.signal`: Receives external input (approval response)
- `@workflow.query`: Exposes workflow state (pending approval, status)
