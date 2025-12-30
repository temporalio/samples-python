# Temporal LangGraph Samples

These samples demonstrate the Temporal LangGraph integration - combining LangGraph's agent framework with Temporal's durable execution.

> **Note:** The LangGraph integration is currently available as a preview feature in the `langgraph_plugin` branch of the SDK repository.

## Overview

The integration combines:
- **Temporal workflows** for orchestrating agent control flow and state management
- **LangGraph** for defining agent graphs with conditional logic, cycles, and state

This approach ensures that AI agent workflows are durable, observable, and can handle failures gracefully.

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- Python 3.9+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

## Installation

Since the LangGraph integration is currently in a branch, you need to install from the branch repositories.

### Running the Samples

1. Clone this samples repository:
   ```bash
   git clone -b langgraph_plugin https://github.com/mfateev/samples-python.git
   cd samples-python
   ```

2. Install dependencies:
   ```bash
   uv sync --group langgraph
   ```

3. Install the SDK from the `langgraph-plugin` branch:
   ```bash
   uv pip install "temporalio @ git+https://github.com/mfateev/sdk-python.git@langgraph-plugin"
   ```

4. Start a local Temporal server:
   ```bash
   temporal server start-dev
   ```

5. Navigate to a sample directory and follow its README for specific instructions

## Examples

Each directory contains a complete example with its own README for detailed instructions:

| Sample | Description |
|--------|-------------|
| [hello_world](./hello_world/) | Simple starter example demonstrating basic plugin setup and graph registration |
| [activity_from_node](./activity_from_node/) | Calling Temporal activities from a graph node using run_in_workflow |
| [react_agent](./react_agent/) | ReAct agent pattern with tool calling and multi-step reasoning |
| [approval_workflow](./approval_workflow/) | Human-in-the-loop with interrupt/resume for approval workflows |
| [supervisor](./supervisor/) | Multi-agent supervisor pattern coordinating specialized agents |
| [agentic_rag](./agentic_rag/) | Retrieval-augmented generation with document grading and query rewriting |
| [deep_research](./deep_research/) | Multi-step research with web search and iterative refinement |
| [plan_and_execute](./plan_and_execute/) | Plan-and-execute pattern with structured step execution |
| [reflection](./reflection/) | Self-reflection pattern for iterative improvement |
