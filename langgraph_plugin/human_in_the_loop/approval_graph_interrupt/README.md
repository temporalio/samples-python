# Human-in-the-Loop Approval Workflow

A workflow demonstrating human-in-the-loop approval using LangGraph's `interrupt()` function with Temporal signals, queries, and notification activities.

## What This Sample Demonstrates

- **LangGraph interrupt**: Using `interrupt()` to pause graph execution for human input
- **Notification activity**: Alerting approvers when approval is needed
- **Temporal signals**: Receiving approval/rejection decisions from external systems
- **Temporal queries**: Checking pending approval status and workflow state
- **CLI response tool**: Separate script for approvers to respond to requests
- **Timeout handling**: Optional approval deadlines with auto-rejection

## How It Works

1. **process_request**: Validates the request and determines risk level based on amount
2. **request_approval**: Calls `interrupt()` to pause execution and wait for human input
3. **notify_approver** (activity): Sends notification with instructions on how to respond
4. **execute_action**: Processes the approved request or handles rejection

The workflow flow:
```
Request → [Process & Assess Risk] → [Interrupt] → [Notify Approver] → [Wait for Signal] → [Execute or Reject] → Result
```

## Prerequisites

- Temporal server running locally (`temporal server start-dev`)

## Running the Example

**Terminal 1 - Start the worker:**
```bash
uv run langgraph_plugin/human_in_the_loop/approval_graph_interrupt/run_worker.py
```

**Terminal 2 - Start a workflow:**
```bash
uv run langgraph_plugin/human_in_the_loop/approval_graph_interrupt/run_workflow.py
```

The worker will print notification instructions like:
```
*** APPROVAL NEEDED ***
Workflow ID: approval-abc12345
Request: Please approve purchase for $500.00 (Risk: medium)

To respond, run:
  Approve: uv run langgraph_plugin/human_in_the_loop/approval_graph_interrupt/run_respond.py approval-abc12345 --approve --reason 'Your reason'
  Reject:  uv run langgraph_plugin/human_in_the_loop/approval_graph_interrupt/run_respond.py approval-abc12345 --reject --reason 'Your reason'
```

**Terminal 3 - Respond to the approval request:**
```bash
# Check status
uv run langgraph_plugin/human_in_the_loop/approval_graph_interrupt/run_respond.py approval-abc12345 --status

# Approve
uv run langgraph_plugin/human_in_the_loop/approval_graph_interrupt/run_respond.py approval-abc12345 --approve --reason "Within budget"

# Or reject
uv run langgraph_plugin/human_in_the_loop/approval_graph_interrupt/run_respond.py approval-abc12345 --reject --reason "Needs manager approval"
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
Starting approval workflow: approval-abc12345
Workflow started. Waiting for result...

To approve/reject, use the run_respond script (see worker output for commands)

============================================================
Result: Successfully processed purchase for $500.00. Approved by cli-user: Within budget
Executed: True
```

## Key APIs Used

- `interrupt(value)`: Pauses graph execution and returns `value` in `__interrupt__`
- `Command(resume=response)`: Resumes graph execution with the given response
- `@activity.defn`: Notification activity to alert approvers
- `@workflow.signal`: Receives external input (approval response)
- `@workflow.query`: Exposes workflow state (pending approval, status)
