# Human-in-the-Loop (Functional API)

A workflow that pauses for human approval using `interrupt()` before executing actions.

## Overview

The human-in-the-loop pattern demonstrates how to pause a workflow for external input:

1. **Process** - Validate and assess the request
2. **Interrupt** - Pause workflow, wait for human approval
3. **Execute** - Complete action based on approval decision

## Architecture

```
Approval Request
      │
      ▼
┌─────────────────┐
│ process_request │
│     (task)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   interrupt()   │ ◄── Workflow pauses here
│  (wait signal)  │
└────────┬────────┘
         │
    Signal received
         │
         ▼
┌─────────────────┐
│ execute_action  │
│     (task)      │
└─────────────────┘
```

## Key Code

### Using interrupt()

```python
@entrypoint()
async def approval_entrypoint(
    request_type: str,
    amount: float,
    request_data: dict | None = None,
) -> dict:
    # Step 1: Validate the request
    validation = await process_request(request_type, amount, request_data)

    # Step 2: Pause for human approval
    approval_request = {
        "request_type": request_type,
        "amount": amount,
        "risk_level": validation["risk_level"],
        "message": f"Please approve {request_type} for ${amount:.2f}",
    }

    # interrupt() pauses the workflow and returns when signal is received
    approval_response = interrupt(approval_request)

    # Step 3: Execute based on approval
    approved = approval_response.get("approved", False)
    result = await execute_action(request_type, amount, approved, ...)

    return {"approved": approved, **result}
```

### Temporal Workflow Wrapper

```python
@workflow.defn
class ApprovalWorkflow:
    def __init__(self):
        self._pending_approval: dict | None = None
        self._approval_response: dict | None = None

    @workflow.run
    async def run(self, request: ApprovalRequest) -> dict:
        runner = compile_functional(approval_entrypoint)

        async for event in runner.astream_events(...):
            if event["event"] == "on_interrupt":
                self._pending_approval = event["data"]
                await workflow.wait_condition(
                    lambda: self._approval_response is not None
                )
                # Resume with approval response
                runner.update_state(..., {"resuming": self._approval_response})

    @workflow.query
    def get_pending_approval(self) -> dict | None:
        return self._pending_approval

    @workflow.signal
    def provide_approval(self, response: dict) -> None:
        self._approval_response = response
```

### Client Interaction

```python
# Start workflow
handle = await client.start_workflow(ApprovalWorkflow.run, request, ...)

# Query pending approval
pending = await handle.query(ApprovalWorkflow.get_pending_approval)
print(f"Needs approval: {pending['message']}")

# Provide approval via signal
await handle.signal(ApprovalWorkflow.provide_approval, {
    "approved": True,
    "approver": "manager@example.com",
    "reason": "Approved for vendor payment",
})

# Get result
result = await handle.result()
```

## Why Temporal?

- **Durable pause**: Workflow survives restarts while waiting for approval
- **Query state**: Check pending approvals without database
- **Signal resume**: Resume with approval via Temporal signals
- **Timeout handling**: Add deadlines for approvals
- **Audit trail**: Full history of approval workflow

## Running the Sample

1. Start Temporal:
   ```bash
   temporal server start-dev
   ```

2. Run the worker:
   ```bash
   uv run langgraph_plugin/functional_api/human_in_the_loop/run_worker.py
   ```

3. Execute workflow with approval:
   ```bash
   uv run langgraph_plugin/functional_api/human_in_the_loop/run_workflow.py
   ```

## Customization

### Add Approval Timeout

```python
@workflow.run
async def run(self, request: ApprovalRequest) -> dict:
    # Wait for approval with timeout
    try:
        await workflow.wait_condition(
            lambda: self._approval_response is not None,
            timeout=timedelta(hours=24),
        )
    except asyncio.TimeoutError:
        return {"status": "expired", "message": "Approval timed out"}
```

### Multi-Level Approval

```python
@entrypoint()
async def multi_approval_entrypoint(request: dict) -> dict:
    # First level: Manager approval
    manager_response = interrupt({"level": "manager", ...})

    if request["amount"] > 10000:
        # Second level: Director approval for large amounts
        director_response = interrupt({"level": "director", ...})

    return await execute_action(...)
```

### Risk-Based Routing

```python
@entrypoint()
async def risk_based_entrypoint(request: dict) -> dict:
    validation = await assess_risk(request)

    if validation["risk_level"] == "low":
        # Auto-approve low risk
        return await execute_action(request, auto_approved=True)
    else:
        # Require human approval for medium/high risk
        approval = interrupt({"risk_level": validation["risk_level"], ...})
        return await execute_action(request, approved=approval["approved"])
```
