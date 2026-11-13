# Human in the loop

A tool that runs only after a person approves. `delete_file` carries `approval_mode="always_require"`, Agent Framework's own approval setting. The run returns with the request in `response.user_input_requests` instead of calling the tool. The Workflow publishes the request through the `pending_approvals` Query, waits for the `decide` Update, and sends the decision back with `request.to_function_approval_response(approved)` on the same session. Agent Framework keys the approval by the function call's id, which the plugin records in history, so the request survives a Worker restart.

## What this sample demonstrates

- `@tool(approval_mode="always_require")` and the `while response.user_input_requests` loop
- A Query for what is pending and an Update for the decision. The validator accepts only `approve` or `reject`, so anything else never enters history. It checks the input and not the Workflow's state: validators run before the Workflow coroutine applies the other events of the same Workflow Task, so a decision that lands in the same task as the model's reply would see no pending request yet.
- The approved tool runs in the Workflow; a rejected one never runs, and the model gets Agent Framework's rejection result

## Running the sample

```bash
# Terminal 1
uv run agent_framework_plugin/human_in_the_loop/run_worker.py

# Terminal 2
uv run agent_framework_plugin/human_in_the_loop/run_workflow.py
```

The starter polls the Query, prints `Approval requested: delete_file({'path': '/tmp/report.txt'})`, sends `approve`, prints `Decision: approve` and then the agent's report. Send `reject` instead to see the rejection path. The Workflow `agent-framework-human-in-the-loop` shows two `agent_framework.invoke_model` Activities: the request and the report.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `delete_file`, `ApprovalRequest` and `HumanInTheLoopWorkflow` |
| `run_worker.py` | Registers the plugin, starts the Worker |
| `run_workflow.py` | Starts the Workflow, polls the Query, sends the Update, prints the result |
