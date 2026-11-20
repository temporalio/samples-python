# Human in the loop

A tool that runs only after a person approves. `delete_file` carries `approval_mode="always_require"`, Agent Framework's own approval setting. The run returns with the request in `response.user_input_requests` instead of calling the tool. The Workflow publishes the request through the `pending_approvals` Query, waits for a `decide` Update carrying `Decision(request_id, approved)` for each request, and sends the decisions back with `request.to_function_approval_response(approved)` on the same session. Agent Framework keys the approval by the function call's id, which the plugin records in history, so the request survives a Worker restart.

## What this sample demonstrates

- `@tool(approval_mode="always_require")` and the `while response.user_input_requests` loop
- A Query for what is pending and an Update keyed by request id. The validator checks only the input (a non-empty `request_id`), so bad input never enters history. The handler fails the Update with an `ApplicationError` for an id that is already decided or not pending, so a double submit or a typo cannot answer a later request.
- Why the handler waits for the model's reply to be read first: a decision can land in the same Workflow Task as the reply that raised the request, and validators and handlers run before the loop in `run` has read that reply.
- The approved tool runs in the Workflow; a rejected one never runs, and the model gets Agent Framework's rejection result

## Running the sample

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/human_in_the_loop/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/human_in_the_loop/run_workflow.py
```

The starter polls the Query, prints `Approval requested: delete_file({'path': '/tmp/report.txt'})`, sends `Decision(request_id=..., approved=True)` with the id the Query returned, prints `Decision: approved` and then the agent's report. Set `approved=False` in `run_workflow.py` to see the rejection path. The Workflow `microsoft-agent-framework-human-in-the-loop` shows two `microsoft_agent_framework.invoke_model` Activities: the request and the report.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `delete_file`, `ApprovalRequest`, `Decision` and `HumanInTheLoopWorkflow` |
| `run_worker.py` | Registers the plugin, starts the Worker |
| `run_workflow.py` | Starts the Workflow, polls the Query, sends the Update, prints the result |
