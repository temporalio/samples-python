# LangGraph Functional API + Temporal Integration Proposal

This sample demonstrates the **proposed** integration between LangGraph's Functional API and Temporal using `LangGraphFunctionalPlugin`.

> ⚠️ **Note**: `LangGraphFunctionalPlugin` is a **proposal** and does not exist yet. This sample shows the intended developer experience.

## Key Insights

### 1. `@entrypoint` returns `Pregel`

`@entrypoint` returns a `Pregel` object (same as `StateGraph.compile()`), so we can use the same `compile("name")` API in workflows.

### 2. No Explicit Task Registration Needed

LangGraph **doesn't pre-register tasks**. When `@task` functions are called:
1. They go through `CONFIG_KEY_CALL` callback in the config
2. The callback receives the **actual function object**
3. `identifier(func)` returns `module.qualname` (e.g., `mymodule.research_topic`)

This means the Temporal plugin can discover tasks **dynamically at runtime**:
- Inject `CONFIG_KEY_CALL` callback that schedules a dynamic activity
- The activity receives function identifier + serialized args
- The activity imports the function by module path and executes it

**The worker just needs the task modules to be importable.**

## Overview

```python
# NO explicit task registration!
# Pass entrypoints as list - names extracted from func.__name__
plugin = LangGraphFunctionalPlugin(
    entrypoints=[document_workflow, review_workflow],
)
```

Key mappings:
- **`@task` calls → Dynamic Activities**: Discovered at runtime via `CONFIG_KEY_CALL`
- **`@entrypoint` functions → Pregel graphs**: Executed via `compile()` in workflows
- **`interrupt()` → User-handled signals**: Workflow controls pause/resume

## How It Works Internally

```python
# When you call a @task function:
result = await research_topic("AI")

# Internally, @task wraps this in call():
fut = call(research_topic_func, "AI", ...)

# call() reads CONFIG_KEY_CALL from config:
config = get_config()
impl = config[CONF][CONFIG_KEY_CALL]
fut = impl(func, args, ...)  # func is the actual function object!

# The plugin's callback:
# 1. Gets identifier: "langgraph_plugin.functional_api_proposal.tasks.research_topic"
# 2. Schedules dynamic activity with identifier + args
# 3. Activity imports function and executes it
```

## Developer Experience

### 1. Define Tasks

```python
# tasks.py
from langgraph.func import task

@task
async def research_topic(topic: str) -> dict:
    """Discovered dynamically when called."""
    return {"facts": [...]}

@task
async def write_section(topic: str, section: str, research: dict) -> str:
    return f"Content about {topic}..."
```

### 2. Define Entrypoints

```python
# entrypoint.py
from langgraph.func import entrypoint
from langgraph.types import interrupt
from .tasks import research_topic, write_section

@entrypoint()
async def document_workflow(topic: str) -> dict:
    # Task calls discovered at runtime via CONFIG_KEY_CALL
    research = await research_topic(topic)

    intro = write_section(topic, "intro", research)
    body = write_section(topic, "body", research)
    sections = [await intro, await body]

    return {"sections": sections}
```

### 3. Define Temporal Workflows

```python
# workflow.py
from temporalio import workflow
from temporalio.contrib.langgraph import compile

@workflow.defn
class DocumentWorkflow:
    @workflow.run
    async def run(self, topic: str) -> dict:
        app = compile("document_workflow")
        result = await app.ainvoke(topic)
        return result
```

### 4. Register with Plugin (No Task Registration!)

```python
# run_worker.py
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin

# NO tasks={} needed!
# Pass entrypoints as list - names extracted from func.__name__
plugin = LangGraphFunctionalPlugin(
    entrypoints=[document_workflow, review_workflow],
    # Optional: default timeout for all task activities
    default_task_timeout=timedelta(minutes=10),
    # Optional: per-task options by function name
    task_options={
        "research_topic": {
            "start_to_close_timeout": timedelta(minutes=15),
        },
    },
)

worker = Worker(
    client,
    task_queue="langgraph-functional",
    workflows=[DocumentWorkflow, ReviewWorkflow],
)
```

Note: In workflows, you still use `compile("document_workflow")` by name string
because the workflow sandbox restricts imports (Pregel isn't sandbox-safe).

## Sample Structure

```
functional_api_proposal/
├── tasks.py          # @task functions (discovered dynamically)
├── entrypoint.py     # @entrypoint functions (→ Pregel)
├── workflow.py       # User-defined Temporal workflows
├── run_worker.py     # Plugin setup (no task registration!)
├── run_workflow.py   # Execute workflows
└── README.md
```

## Running the Sample

```bash
# 1. Start Temporal
temporal server start-dev

# 2. Start Worker
python -m langgraph_plugin.functional_api_proposal.run_worker

# 3. Run Workflows
python -m langgraph_plugin.functional_api_proposal.run_workflow document
python -m langgraph_plugin.functional_api_proposal.run_workflow review
```

## Implementation Details

### Dynamic Activity Execution

The plugin provides a single dynamic activity:

```python
@activity.defn(name="execute_langgraph_task")
async def execute_task(task_id: str, args: bytes, kwargs: bytes) -> bytes:
    """Execute any @task function by module path."""
    # Import the function
    module_name, func_name = task_id.rsplit(".", 1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)

    # Execute
    result = await func(*deserialize(args), **deserialize(kwargs))
    return serialize(result)
```

### CONFIG_KEY_CALL Injection

When `compile()` is called in a workflow, the plugin injects a custom callback:

```python
def temporal_call_callback(func, args, retry_policy, cache_policy, callbacks):
    task_id = identifier(func)  # e.g., "mymodule.research_topic"

    # Schedule the dynamic activity
    return workflow.execute_activity(
        "execute_langgraph_task",
        args=(task_id, serialize(args)),
        start_to_close_timeout=get_timeout(task_id),
        retry_policy=convert_retry_policy(retry_policy),
    )
```

## Comparison with Graph API

| Aspect | Graph API | Functional API |
|--------|-----------|----------------|
| Definition | `StateGraph` + `add_node()` | `@task` + `@entrypoint` |
| Control flow | Graph edges | Python code |
| Returns | `Pregel` | `Pregel` |
| In-workflow API | `compile("name")` | `compile("name")` |
| Activity discovery | From graph nodes | Dynamic via `CONFIG_KEY_CALL` |
| Registration | `graphs={name: builder}` | `entrypoints=[func, ...]` |

## Why This Works

1. **LangGraph's extensibility**: `CONFIG_KEY_CALL` is designed for custom execution backends
2. **Function identification**: `identifier()` provides stable module paths
3. **Dynamic activities**: Temporal supports activity execution by name
4. **Serialization**: Args/results serialized for activity transport
