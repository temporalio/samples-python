# Multi-agent

A coordinator agent with two sub-agents as tools. `researcher.as_tool()` and `writer.as_tool()` are Agent Framework's own way to delegate; the coordinator decides when to call them. All three agents run in the Workflow, and every model call any of them makes is an Activity, so the whole tree is durable with no per-agent wiring.

Each agent has its own `TemporalChatClient` with a `summary`, so the Activities read `coordinator`, `researcher`, `coordinator`, `writer`, `coordinator` in the Temporal UI. `Agent.as_tool()` runs the sub-agent streaming, so the two sub-agent calls are `agent_framework.invoke_model_streaming` Activities and the coordinator's three are `agent_framework.invoke_model`.

## What this sample demonstrates

- `Agent(tools=[researcher.as_tool(), writer.as_tool()])`
- One `TemporalChatClient` per agent, with `summary=` naming the agent
- Five model Activities in one Workflow run

## Running the sample

```bash
# Terminal 1
uv run agent_framework_plugin/multi_agent/run_worker.py

# Terminal 2
uv run agent_framework_plugin/multi_agent/run_workflow.py
```

The starter prints the writer's paragraph as relayed by the coordinator. The Workflow `agent-framework-multi-agent` shows the five Activities above.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `chat_client` and `MultiAgentWorkflow` with the three agents |
| `run_worker.py` | Registers the plugin, starts the Worker |
| `run_workflow.py` | Executes the Workflow and prints the result |
