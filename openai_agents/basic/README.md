# Basic Agent Examples

Simple examples to get started with OpenAI Agents SDK integrated with Temporal workflows.

*Adapted from [OpenAI Agents SDK basic examples](https://github.com/openai/openai-agents-python/tree/main/examples/basic)*

Before running these examples, be sure to review the [prerequisites and background on the integration](../README.md).

## Running the Examples

First, start the worker (supports all basic examples):
```bash
uv run openai_agents/basic/run_worker.py
```

Then run individual examples in separate terminals:

### Hello World Agent
Basic agent that only responds in haikus:
```bash
uv run openai_agents/basic/run_hello_world_workflow.py
```

### Tools Agent
Agent with access to external tools (simulated weather API):
```bash
uv run openai_agents/basic/run_tools_workflow.py
```

### Agent Lifecycle with Hooks
Demonstrates agent lifecycle events and handoffs between agents:
```bash
uv run openai_agents/basic/run_agent_lifecycle_workflow.py
```

### Lifecycle with Usage Tracking
Shows detailed usage tracking with RunHooks (requests, tokens, etc.):
```bash
uv run openai_agents/basic/run_lifecycle_workflow.py
```

### Dynamic System Prompts
Agent with dynamic instruction generation based on context (haiku/pirate/robot):
```bash
uv run openai_agents/basic/run_dynamic_system_prompt_workflow.py
```

### Non-Strict Output Types
Demonstrates different JSON schema validation approaches:
```bash
uv run openai_agents/basic/run_non_strict_output_workflow.py
```

Note: `CustomOutputSchema` is not supported by the Temporal OpenAI Agents SDK integration and is omitted in this example.

### Image Processing - Local
Process local image files with AI vision:
```bash
uv run openai_agents/basic/run_local_image_workflow.py
```

### Image Processing - Remote
Process remote image URLs with AI vision:
```bash
uv run openai_agents/basic/run_remote_image_workflow.py
```

### Previous Response ID
Demonstrates conversation continuity using response IDs:
```bash
uv run openai_agents/basic/run_previous_response_id_workflow.py
```

## Omitted Examples

The following examples from the [reference repository](https://github.com/openai/openai-agents-python/tree/main/examples/basic) are not included in this Temporal adaptation:

- **Session** - Stores state in local SQLite database, not appropriate for distributed workflows
- **Stream Items/Stream Text** - Streaming is not supported in Temporal OpenAI Agents SDK integration