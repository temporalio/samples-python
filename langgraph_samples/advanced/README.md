# Advanced Pattern Samples

This directory contains samples demonstrating advanced LangGraph patterns with Temporal integration.

## Available Samples

### [Reflection Agent](./reflection/README.md)

An agent that generates content, critiques it, and iteratively improves until quality criteria are met.

**Key Features:**
- Generate-critique-revise loop
- Structured feedback with quality scoring
- Quality-based termination (score >= 7)
- Maximum iteration limits
- Full critique history visibility

## Why Advanced Patterns?

These patterns demonstrate sophisticated agent behaviors:
- **Self-improvement**: Agents that refine their own outputs
- **Quality assurance**: Automatic quality checking and iteration
- **Transparency**: Full visibility into the improvement process

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- OpenAI API key set: `export OPENAI_API_KEY=your-key`
- Dependencies installed via `uv sync --group langgraph`
