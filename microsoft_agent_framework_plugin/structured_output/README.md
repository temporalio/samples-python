# Structured output

The agent fills a Pydantic model. `agent.run(prompt, options={"response_format": PersonInfo})` sends the model's JSON schema to the model Activity, and the Workflow reads the parsed `PersonInfo` from `response.value`. The Workflow returns the model itself: the plugin sets Temporal's Pydantic data converter, so the typed value crosses the Workflow boundary without extra setup.

## What this sample demonstrates

- `options={"response_format": PersonInfo}` and `response.value`
- A Workflow whose return type is a Pydantic model
- `MicrosoftAgentFrameworkPlugin()` on the starter's Client too, so the starter decodes the result with the same converter

## Running the sample

```bash
# Terminal 1
uv run microsoft_agent_framework_plugin/structured_output/run_worker.py

# Terminal 2
uv run microsoft_agent_framework_plugin/structured_output/run_workflow.py
```

The starter prints `name=John Smith age=30 occupation=software engineer`. The Workflow `microsoft-agent-framework-structured-output` shows one `microsoft_agent_framework.invoke_model` Activity.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `PersonInfo` and `StructuredOutputWorkflow` |
| `run_worker.py` | Registers the plugin, starts the Worker |
| `run_workflow.py` | Executes the Workflow and prints the typed result |
