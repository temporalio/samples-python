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

## LangGraph API Styles

LangGraph provides two API styles for defining workflows:

| Aspect | Graph API | Functional API |
|--------|-----------|----------------|
| Definition | `StateGraph` + `add_node()` + `add_edge()` | `@task` + `@entrypoint` |
| Control flow | Explicit graph edges | Python code (loops, conditionals) |
| State | Shared TypedDict with reducers | Function arguments/returns |
| Parallelism | Send API, conditional edges | Concurrent task calls |
| Compile | `compile(graph, "id")` | `compile_functional("id")` |

## Examples

Examples are organized by API style:

### Graph API (`graph_api/`)

StateGraph-based examples using nodes and edges:

| Sample | Description |
|--------|-------------|
| [hello_world](./graph_api/hello_world/) | Simple starter example demonstrating basic plugin setup and graph registration |
| [activity_from_node](./graph_api/activity_from_node/) | Calling Temporal activities from a graph node using run_in_workflow |
| [react_agent](./graph_api/react_agent/) | ReAct agent pattern with tool calling and multi-step reasoning |
| [human_in_the_loop](./graph_api/human_in_the_loop/) | Human-in-the-loop approval workflows using two approaches |
| ↳ [approval_graph_interrupt](./graph_api/human_in_the_loop/approval_graph_interrupt/) | Uses LangGraph's `interrupt()` function |
| ↳ [approval_wait_condition](./graph_api/human_in_the_loop/approval_wait_condition/) | Uses `run_in_workflow=True` with `workflow.wait_condition()` |
| [supervisor](./graph_api/supervisor/) | Multi-agent supervisor pattern coordinating specialized agents |
| [agentic_rag](./graph_api/agentic_rag/) | Retrieval-augmented generation with document grading and query rewriting |
| [deep_research](./graph_api/deep_research/) | Multi-step research with web search and iterative refinement |
| [plan_and_execute](./graph_api/plan_and_execute/) | Plan-and-execute pattern with structured step execution |
| [reflection](./graph_api/reflection/) | Self-reflection pattern for iterative improvement |

### Functional API (`functional_api/`)

`@task` and `@entrypoint` decorator-based examples:

| Sample | Description |
|--------|-------------|
| [functional_api](./functional_api/) | Document creation workflow demonstrating tasks and entrypoints |
