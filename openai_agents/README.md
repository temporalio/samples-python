# Temporal OpenAI Agents SDK Integration

⚠️ **Public Preview** - This integration is experimental and its interfaces may change prior to General Availability.

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

## Examples

Each directory contains a complete example with its own README for detailed instructions:

- **[Basic Examples](./basic/README.md)** - Simple agent examples including a hello world agent and a tools-enabled agent that can access external APIs like weather services.
- **[Agent Patterns](./agent_patterns/README.md)** - Advanced patterns for agent composition, including using agents as tools within other agents.
- **[Tools](./tools/README.md)** - Demonstrates available tools such as file search, image generation, and others.
- **[Handoffs](./handoffs/README.md)** - Agents collaborating via handoffs.
- **[Hosted MCP](./hosted_mcp/README.md)** - Using the MCP client functionality of the OpenAI Responses API.
- **[MCP](./mcp/README.md)** - Local MCP servers (filesystem/stdio, streamable HTTP, SSE, prompt server) integrated with Temporal workflows.
- **[Model Providers](./model_providers/README.md)** - Using custom LLM providers (e.g., Anthropic via LiteLLM).
- **[Research Bot](./research_bot/README.md)** - Multi-agent research system with specialized roles: a planner agent, search agent, and writer agent working together to conduct comprehensive research.
- **[Customer Service](./customer_service/README.md)** - Interactive customer service agent with escalation capabilities, demonstrating conversational workflows.
- **[Reasoning Content](./reasoning_content/README.md)** - Example of how to retrieve the thought process of reasoning models.
- **[Financial Research Agent](./financial_research_agent/README.md)** - Multi-agent financial research system with planner, search, analyst, writer, and verifier agents collaborating.
