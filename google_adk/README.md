# Temporal Google ADK Integration

This directory contains samples demonstrating how to use [Google's Agent Development Kit (ADK)](https://github.com/google/adk-python) with Temporal's durable execution engine.

See the [module documentation](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/google_adk_agents/README.md) for more information.

## Overview

The integration combines:
- **Temporal workflows** for durable orchestration, retries, and state management
- **Google ADK** for AI agent creation with Gemini models and tool interactions

Every LLM call and tool execution is wrapped in a Temporal Activity, making agent workflows replay-safe, retryable, and observable.

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- Required dependencies installed via `uv sync --group google-adk`
- Google API key set as environment variable: `export GOOGLE_API_KEY=your_key_here`

## Examples

Each directory contains a complete example with its own instructions:

### [Basic Examples](./basic/)

Simple agent examples demonstrating core integration patterns:

- **Hello World** — A minimal agent that responds in haikus
- **Tools** — An agent with activity-backed tools (weather, web search)

```bash
# Terminal 1: Start the worker
uv run google_adk/basic/run_worker.py

# Terminal 2: Run a workflow
uv run google_adk/basic/run_hello_world_workflow.py
uv run google_adk/basic/run_tools_workflow.py
```

### [Orchestration](./orchestration/)

Multi-agent orchestration patterns — sequential pipelines, parallel fan-out, and iterative loops:

- **Sequential** — Researcher → Writer → Editor pipeline via chained agent calls
- **Parallel** — Multiple agents answer the same question from different perspectives simultaneously
- **Loop** — Agent iterates on its own output until a termination condition is met

```bash
# Terminal 1: Start the worker
uv run google_adk/orchestration/run_worker.py

# Terminal 2: Run an orchestration
uv run google_adk/orchestration/run_sequential_workflow.py
uv run google_adk/orchestration/run_parallel_workflow.py
uv run google_adk/orchestration/run_loop_workflow.py
```

### [Human-in-the-Loop](./human_in_the_loop/)

Demonstrates pausing agent execution for human approval before sensitive tool calls:

- Agent attempts a sensitive action (send email, delete record)
- Workflow pauses and exposes pending approvals via `@workflow.query`
- External process approves/rejects via `@workflow.signal`
- Agent resumes or reports rejection

```bash
# Terminal 1: Start the worker
uv run google_adk/human_in_the_loop/run_worker.py

# Terminal 2: Run the HITL workflow (starts workflow, polls for approvals, approves)
uv run google_adk/human_in_the_loop/run_hitl_workflow.py
```

## Key Integration Patterns

| Pattern | How It Works |
|---------|-------------|
| **Plugin** | `GoogleAdkPlugin` on `Client.connect()` — handles ADK/Pydantic serialization |
| **TemporalModel** | Wraps Gemini model calls as Temporal Activities for durability |
| **activity_tool** | Wraps `@activity.defn` functions as ADK-compatible tools |
| **InMemoryRunner** | ADK's runner executes the agent within the workflow |
| **Signals for HITL** | `@workflow.signal` enables external approval/rejection of tool calls |
| **Queries for observability** | `@workflow.query` exposes pending state without advancing the workflow |
