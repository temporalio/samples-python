# Basic Agent Examples

Simple examples to get started with OpenAI Agents SDK integrated with Temporal workflows.

*Adapted from [OpenAI Agents SDK basic examples](https://github.com/openai/openai-agents-python/tree/main/examples/basic)*

## Running the Examples

First, start the worker (supports all basic examples):
```bash
uv run openai_agents/basic/run_worker.py
```

Then run individual examples in separate terminals:

### Hello World Agent
```bash
uv run openai_agents/basic/run_hello_world_workflow.py
```

### Tools Agent
Agent with access to external tools (weather API):
```bash
uv run openai_agents/basic/run_tools_workflow.py
```