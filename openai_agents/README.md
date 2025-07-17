# Temporal OpenAI Agents SDK Integration

⚠️ **Experimental** - This module is not yet stable and may change in the future.

This directory contains samples demonstrating how to use the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) with Temporal's durable execution engine.
These samples are adapted from the [OpenAI Agents SDK examples](https://github.com/openai/openai-agents-python/tree/main/examples) and extended with Temporal's durability and orchestration capabilities.

See the [module documentation](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/openai_agents/README.md) for more information.

## Overview

The integration combines:
- **Temporal workflows** for orchestrating agent control flow and state management
- **OpenAI Agents SDK** for AI agent creation and tool interactions

This approach ensures that AI agent workflows are durable, observable, and can handle failures gracefully.

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- Required dependencies installed via `uv sync --group openai-agents`
- OpenAI API key set as environment variable: `export OPENAI_API_KEY=your_key_here`

## Running the Examples

1. **Start the worker** (supports all samples):
   ```bash
   uv run openai_agents/run_worker.py
   ```

2. **Run individual samples** in separate terminals:

### Basic Agent Examples

- **Hello World Agent** - Simple agent that responds in haikus:
  ```bash
  uv run openai_agents/run_hello_world_workflow.py
  ```

- **Tools Agent** - Agent with access to external tools (weather API):
  ```bash
  uv run openai_agents/run_tools_workflow.py
  ```

### Advanced Multi-Agent Examples

- **Research Workflow** - Multi-agent research system with specialized roles:
  ```bash
  uv run openai_agents/run_research_workflow.py
  ```
  Features a planner agent, search agent, and writer agent working together.

- **Customer Service Workflow** - Customer service agent with escalation capabilities (interactive):
  ```bash
  uv run openai_agents/run_customer_service_client.py --conversation-id my-conversation-123
  ```

- **Agents as Tools** - Demonstrate using agents as tools within other agents:
  ```bash
  uv run openai_agents/run_agents_as_tools_workflow.py
  ```

