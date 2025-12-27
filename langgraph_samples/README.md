# Temporal LangGraph Samples

These samples demonstrate the [Temporal LangGraph integration](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/langgraph/README.md) - combining LangGraph's agent framework with Temporal's durable execution.

See the [module documentation](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/langgraph/README.md) for more information.

## Overview

The integration combines:
- **Temporal workflows** for orchestrating agent control flow and state management
- **LangGraph** for defining agent graphs with conditional logic, cycles, and state

This approach ensures that AI agent workflows are durable, observable, and can handle failures gracefully.

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- Required dependencies installed via `uv sync --group langgraph`

## Examples

Each directory contains complete examples with their own README for detailed instructions:

- **[Basic Examples](./basic/README.md)** - Simple examples including a hello world agent demonstrating basic plugin setup and graph registration.
