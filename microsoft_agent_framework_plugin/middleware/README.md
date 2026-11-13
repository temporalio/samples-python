# Middleware

Agent Framework middleware, running in the Workflow. `BlockOutsideTmp` is a `FunctionMiddleware` that refuses `delete_file` calls outside `/tmp` by setting `context.result` and not calling `call_next()`, so the tool never runs and the model reads the refusal. `AppendReminder` is a `ChatMiddleware` that adds one sentence to the instructions of every model call.

Both run inside the Workflow, next to the agent's loop, so a Workflow Definition that uses them must stay deterministic: no clock, no I/O, no randomness in middleware. Middleware that needs I/O calls `await workflow.execute_activity(...)`.

## What this sample demonstrates

- `Agent(middleware=[BlockOutsideTmp(), AppendReminder()])`
- Refusing a tool call from function middleware without an Activity
- Editing `context.options["instructions"]` from chat middleware before the request leaves for the model Activity

## Running the sample

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/middleware/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/middleware/run_workflow.py
```

The prompt asks for two deletes. The agent reports that `/etc/passwd` was refused and `/tmp/scratch.txt` was deleted, in one short sentence because of the reminder. The Workflow `microsoft-agent-framework-middleware` shows three `microsoft_agent_framework.invoke_model` Activities and nothing for the tool calls.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `delete_file`, the two middleware classes and `MiddlewareWorkflow` |
| `run_worker.py` | Registers the plugin, starts the Worker |
| `run_workflow.py` | Executes the Workflow and prints the result |
