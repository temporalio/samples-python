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

Each directory contains complete examples with their own README for detailed instructions:

- **[Basic Examples](./basic/README.md)** - Simple examples including a hello world agent demonstrating basic plugin setup and graph registration.
- **[Human-in-the-Loop](./human_in_loop/README.md)** - Examples demonstrating interrupt/resume workflows with human approval.
- **[Multi-Agent](./multi_agent/README.md)** - Multi-agent patterns including supervisor coordination.
- **[RAG (Retrieval Augmented Generation)](./rag/README.md)** - Intelligent retrieval with document grading, query rewriting, and deep research.
- **[Planning](./planning/README.md)** - Plan-and-execute patterns with structured step execution.
- **[Advanced Patterns](./advanced/README.md)** - Advanced techniques including reflection and self-improvement.
