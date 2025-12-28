# Human-in-the-Loop Samples

This directory contains samples demonstrating human-in-the-loop patterns with Temporal LangGraph integration.

## Available Samples

### [Approval Workflow](./approval_workflow/README.md)

An agent that pauses for human approval before taking actions, using LangGraph's `interrupt()` with Temporal signals.

**Key Features:**
- `interrupt()` for pausing execution
- Temporal signals for receiving human input
- Workflow queries for checking pending approvals
- Durable waiting with automatic timeout handling

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- OpenAI API key set: `export OPENAI_API_KEY=your-key`
- Dependencies installed via `uv sync --group langgraph`
