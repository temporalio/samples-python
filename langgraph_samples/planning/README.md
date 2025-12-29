# Planning Samples

This directory contains samples demonstrating planning patterns with Temporal LangGraph integration.

## Available Samples

### [Plan-and-Execute](./plan_and_execute/README.md)

An agent that separates planning from execution, creating a high-level plan first and then executing each step sequentially with the ability to replan based on results.

**Key Features:**
- Structured planning with explicit steps
- Sequential step execution with available tools
- Dynamic replanning when steps fail
- Progress visibility through Temporal
- Checkpointing after each step

## Why Planning Patterns?

Planning agents offer several advantages:
- **Predictability**: The plan is visible before execution
- **Control**: Users can review/modify plans
- **Resilience**: Failed steps can be replanned
- **Observability**: Progress is tracked step-by-step

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- OpenAI API key set: `export OPENAI_API_KEY=your-key`
- Dependencies installed via `uv sync --group langgraph`
