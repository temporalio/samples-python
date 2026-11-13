# Hello world

The smallest Agent Framework + Temporal sample: one `Agent` over `TemporalChatClient`, invoked once. The model call runs as the `agent_framework.invoke_model` Activity with a 60-second start-to-close timeout, so Temporal retries it and it survives a Worker restart.

## What this sample demonstrates

- `AgentFrameworkPlugin(chat_clients=...)` on the Client, with the `OpenAIChatClient` built on the Worker from `OPENAI_API_KEY`
- `Agent(client=TemporalChatClient("gpt-4o-mini", start_to_close_timeout=...))` in a `@workflow.defn`
- `await agent.run(prompt)` and `response.text`, unchanged from Agent Framework

## Running the sample

Prerequisites: `uv sync --group agent-framework`, `OPENAI_API_KEY` in the Worker's environment, and a Temporal dev server (`temporal server start-dev`). Run both commands from the repository root.

```bash
# Terminal 1
uv run agent_framework_plugin/hello_world/run_worker.py

# Terminal 2
uv run agent_framework_plugin/hello_world/run_workflow.py
```

The starter prints `Result:` and the haiku. In the Temporal UI the Workflow `agent-framework-hello-world` shows one `agent_framework.invoke_model` Activity with the summary `gpt-4o-mini`.

## Files

| File | Description |
|------|-------------|
| `workflow.py` | `HelloWorldWorkflow` with one `Agent` |
| `run_worker.py` | Builds the plugin with the OpenAI chat client factory and starts the Worker |
| `run_workflow.py` | Executes the Workflow and prints the result |
