# Tools

Two tool patterns on one agent:

| Pattern | When to use it |
|---------|----------------|
| `@tool` from `agent_framework` | Pure logic with no I/O. Runs in the Workflow and leaves no Activity. |
| `@activity.defn` wrapped with `activity_as_tool` | Anything with I/O or a clock. Runs as an Activity with its own timeout and retries. |

The prompt exercises both. The history shows one `microsoft_agent_framework.invoke_model` Activity per model turn plus one `fetch_weather` Activity; `letter_counter` runs in the Workflow and does not appear.

## What this sample demonstrates

- `activity_as_tool(fetch_weather, start_to_close_timeout=timedelta(seconds=30))` from `temporalio.microsoft_agent_framework.workflow`; Agent Framework reads the tool's schema from the Activity's signature and docstring
- The plugin cannot tell a pure tool from an I/O tool, so you choose per tool
- Registering the Activity on the Worker next to the Workflow
- A synchronous `def` tool: the plugin runs it on the Workflow's event loop, so keep it quick

## Running the sample

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/tools/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/tools/run_workflow.py
```

The starter prints the agent's answer with the letter count and the weather. The Workflow `microsoft-agent-framework-tools` shows three model Activities and one `fetch_weather` Activity.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `letter_counter`, `fetch_weather` and `ToolsWorkflow` |
| `run_worker.py` | Registers the plugin and the `fetch_weather` Activity, starts the Worker |
| `run_workflow.py` | Executes the Workflow and prints the result |
