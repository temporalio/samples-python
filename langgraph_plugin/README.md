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
| [hello_world](./functional_api/hello_world/) | Simple starter example demonstrating basic plugin setup with `@task` and `@entrypoint` |
| [react_agent](./functional_api/react_agent/) | ReAct agent pattern with tool calling using tasks for model and tool execution |
| [human_in_the_loop](./functional_api/human_in_the_loop/) | Human-in-the-loop approval workflow using `interrupt()` for pause/resume |
| [supervisor](./functional_api/supervisor/) | Multi-agent supervisor pattern with tasks for each agent role |
| [agentic_rag](./functional_api/agentic_rag/) | RAG with document grading and query rewriting using task-based retrieval |
| [deep_research](./functional_api/deep_research/) | Multi-step research with parallel search execution via concurrent tasks |
| [plan_and_execute](./functional_api/plan_and_execute/) | Plan-and-execute pattern with step-by-step task execution |
| [reflection](./functional_api/reflection/) | Self-reflection pattern for iterative content improvement |

## Usage

### Graph API Usage

The Graph API uses `StateGraph` to define nodes and edges, with each node running as a Temporal activity:

```python
from langgraph.graph import StateGraph, START, END
from temporalio import workflow
from temporalio.contrib.langgraph import LangGraphPlugin, compile

# 1. Define your graph
class State(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot(state: State) -> State:
    response = model.invoke(state["messages"])
    return {"messages": [response]}

graph = StateGraph(State)
graph.add_node("chatbot", chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

# 2. Register graph with plugin
plugin = LangGraphPlugin(graphs={"my_graph": graph.compile()})

# 3. Use in workflow
@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, query: str) -> dict:
        app = compile("my_graph")  # Get runner for registered graph
        return await app.ainvoke({"messages": [("user", query)]})

# 4. Start worker with plugin
async with Worker(client, task_queue="q", workflows=[MyWorkflow], plugins=[plugin]):
    result = await client.execute_workflow(MyWorkflow.run, "Hello", ...)
```

### Functional API Usage

The Functional API uses `@task` and `@entrypoint` decorators. Tasks run as Temporal activities:

```python
from langgraph.func import task, entrypoint
from temporalio import workflow
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin, compile_functional

# 1. Define tasks (run as Temporal activities)
@task
def research(topic: str) -> str:
    """Each @task call becomes a Temporal activity."""
    return search_web(topic)

@task
def summarize(content: str) -> str:
    return model.invoke(f"Summarize: {content}")

# 2. Define entrypoint (orchestrates tasks)
@entrypoint()
async def research_workflow(topic: str) -> dict:
    """The entrypoint runs in the workflow, orchestrating tasks."""
    # Tasks can run in parallel
    results = [research(q) for q in generate_queries(topic)]
    content = [await r for r in results]  # Wait for all

    summary = await summarize("\n".join(content))
    return {"summary": summary}

# 3. Register entrypoint with plugin
plugin = LangGraphFunctionalPlugin(
    entrypoints={"research": research_workflow}
)

# 4. Use in workflow
@workflow.defn
class ResearchWorkflow:
    @workflow.run
    async def run(self, topic: str) -> dict:
        app = compile_functional("research")
        return await app.ainvoke(topic)

# 5. Start worker with plugin
async with Worker(client, task_queue="q", workflows=[ResearchWorkflow], plugins=[plugin]):
    result = await client.execute_workflow(ResearchWorkflow.run, "AI trends", ...)
```

### Key Differences

| Feature | Graph API | Functional API |
|---------|-----------|----------------|
| Task definition | Graph nodes | `@task` decorator |
| Orchestration | Graph edges | Python control flow |
| Parallel execution | `Send` API | Concurrent `await` |
| State management | Shared `TypedDict` | Function arguments |
| Compile function | `compile("graph_id")` | `compile_functional("entrypoint_id")` |
| Plugin class | `LangGraphPlugin` | `LangGraphFunctionalPlugin` |

### Configuration Options

Both APIs support activity configuration:

```python
# Graph API - per-node options
plugin = LangGraphPlugin(
    graphs={"my_graph": graph},
    default_start_to_close_timeout=timedelta(minutes=5),
    node_options={
        "expensive_node": {"start_to_close_timeout": timedelta(minutes=30)}
    }
)

# Functional API - per-task options
plugin = LangGraphFunctionalPlugin(
    entrypoints={"my_entrypoint": entrypoint_func},
    default_task_timeout=timedelta(minutes=5),
    task_options={
        "expensive_task": {"start_to_close_timeout": timedelta(minutes=30)}
    }
)
```
