# LangGraph Plugin Samples

These samples demonstrate the [Temporal LangGraph plugin](https://github.com/temporalio/sdk-python/pull/1448), which runs LangGraph workflows as durable Temporal workflows. Each LangGraph graph node (Graph API) or `@task` (Functional API) executes as a Temporal activity with automatic retries, timeouts, and crash recovery.

Samples are organized by API style:

- **Graph API** (`graph_api/`) -- Define workflows as `StateGraph` with nodes and edges.
- **Functional API** (`functional_api/`) -- Define workflows with `@task` and `@entrypoint` decorators for an imperative programming style.

## Samples

| Sample | Graph API | Functional API | Description |
|--------|:---------:|:--------------:|-------------|
| **Hello World** | [graph_api/hello_world](graph_api/hello_world) | [functional_api/hello_world](functional_api/hello_world) | Minimal sample -- single node/task that processes a query string. Start here. |
| **Human-in-the-loop** | [graph_api/human_in_the_loop](graph_api/human_in_the_loop) | [functional_api/human_in_the_loop](functional_api/human_in_the_loop) | Chatbot that uses `interrupt()` to pause for human approval, Temporal signals to receive feedback, and queries to expose the pending draft. |
| **Continue-as-new** | [graph_api/continue_as_new](graph_api/continue_as_new) | [functional_api/continue_as_new](functional_api/continue_as_new) | Multi-stage data pipeline that uses `continue-as-new` with task result caching so previously-completed stages are not re-executed. |
| **ReAct Agent** | [graph_api/react_agent](graph_api/react_agent) | [functional_api/react_agent](functional_api/react_agent) | Tool-calling agent loop. Graph API uses conditional edges; Functional API uses a `while` loop. |
| **Control Flow** | -- | [functional_api/control_flow](functional_api/control_flow) | Demonstrates parallel task execution, `for` loops, and `if/else` branching -- patterns that are natural in the Functional API. |

## Prerequisites

> **Note:** These samples require the LangGraph plugin from [sdk-python#1448](https://github.com/temporalio/sdk-python/pull/1448), which has not been released yet. They will not be runnable until the SDK is published with the `temporalio[langgraph]` extra.

1. Install dependencies:

   ```bash
   uv sync --group langgraph
   ```

2. Start a [Temporal dev server](https://docs.temporal.io/cli#start-dev-server):

   ```bash
   temporal server start-dev
   ```

## Running a Sample

Each sample has two scripts -- start the worker first, then the workflow starter in a separate terminal.

```bash
# Terminal 1: start the worker
uv run langgraph_plugin/<api>/<sample>/run_worker.py

# Terminal 2: start the workflow
uv run langgraph_plugin/<api>/<sample>/run_workflow.py
```

For example, to run the Graph API human-in-the-loop chatbot:

```bash
# Terminal 1
uv run langgraph_plugin/graph_api/human_in_the_loop/run_worker.py

# Terminal 2
uv run langgraph_plugin/graph_api/human_in_the_loop/run_workflow.py
```

## Key Features Demonstrated

- **Durable execution** -- Every graph node / `@task` runs as a Temporal activity with configurable timeouts and retry policies.
- **Human-in-the-loop** -- LangGraph's `interrupt()` pauses the graph; Temporal signals deliver human input; queries expose pending state to UIs.
- **Continue-as-new with caching** -- `get_cache()` captures completed task results; passing the cache to the next execution avoids re-running them.
- **Conditional routing** -- Graph API's `add_conditional_edges` and Functional API's native `if/else`/`while` for agent loops.
- **Parallel execution** -- Functional API launches multiple tasks concurrently by creating futures before awaiting them.

## Related

- [SDK PR: LangGraph plugin](https://github.com/temporalio/sdk-python/pull/1448)
