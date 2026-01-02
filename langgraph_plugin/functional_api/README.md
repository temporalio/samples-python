# LangGraph Functional API + Temporal Integration Proposal

This sample demonstrates the **proposed** integration between LangGraph's Functional API and Temporal using `LangGraphFunctionalPlugin`.

> ⚠️ **Note**: `LangGraphFunctionalPlugin` is a **proposal** and does not exist yet. This sample shows the intended developer experience.

## Design Approach

### Core Principle: Entrypoints Run in Workflow Sandbox

The `@entrypoint` function runs **directly in the Temporal workflow sandbox**, not in an activity. This works because:

1. **LangGraph modules passed through sandbox** - `langgraph`, `langchain_core`, `pydantic_core`, etc.
2. **LangGraph machinery is deterministic** - `Pregel`, `call()`, `CONFIG_KEY_CALL` are all deterministic operations
3. **@task calls routed to activities** - via `CONFIG_KEY_CALL` injection
4. **Sandbox enforces determinism** - `time.time()`, `random()`, etc. in entrypoint code is rejected

This aligns with LangGraph's own checkpoint/replay model where:
- Task results are cached for replay
- Entrypoint control flow must be deterministic
- Non-deterministic operations belong in tasks

### Execution Model

```
┌─────────────────────────────────────────────────────────────┐
│  Temporal Workflow (sandbox)                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  @entrypoint function (runs in workflow sandbox)      │  │
│  │                                                       │  │
│  │  research = await research_topic(topic)               │  │
│  │              └──── CONFIG_KEY_CALL ──────────────────────► Activity
│  │                                                       │  │
│  │  intro = write_section(topic, "intro", research)      │  │
│  │  body = write_section(topic, "body", research)        │  │
│  │          └──── CONFIG_KEY_CALL ──────────────────────────► Activities
│  │                                                       │  │  (parallel)
│  │  sections = [await intro, await body]                 │  │
│  │                                                       │  │
│  │  return {"sections": sections}                        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Why This Design?

**Option rejected: Entrypoint as activity**
- Activities can't schedule other activities
- Would lose per-task durability
- All tasks would be local function calls

**Option chosen: Entrypoint in workflow sandbox**
- Matches LangGraph's determinism expectations
- Per-task durability via activities
- Sandbox catches non-deterministic code
- Same pattern as graph API (traversal in workflow, nodes as activities)

## Key Insights

### 1. `@entrypoint` Returns `Pregel`

`@entrypoint` returns a `Pregel` object (same as `StateGraph.compile()`), so we use the same `compile("name")` API.

### 2. No Explicit Task Registration

LangGraph discovers tasks dynamically via `CONFIG_KEY_CALL`:
- When `@task` is called, `call()` reads callback from config
- Callback receives actual function object
- `identifier(func)` returns `module.qualname`
- Plugin schedules dynamic activity with identifier + args

### 3. Sandbox Passthrough

The plugin configures sandbox to allow LangGraph modules:

```python
restrictions.with_passthrough_modules(
    "pydantic_core",      # Already in graph plugin
    "langchain_core",     # Already in graph plugin
    "annotated_types",    # Already in graph plugin
    "langgraph",          # For functional API
)
```

## Developer Experience

### 1. Define Tasks

```python
# tasks.py
from langgraph.func import task

@task
async def research_topic(topic: str) -> dict:
    """Runs as Temporal activity. Can use time, random, I/O, etc."""
    return {"facts": [...]}

@task
async def write_section(topic: str, section: str, research: dict) -> str:
    """Non-deterministic operations belong here."""
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
    """Runs in workflow sandbox. Must be deterministic."""
    # Task calls become activities
    research = await research_topic(topic)

    # Parallel execution
    intro = write_section(topic, "intro", research)
    body = write_section(topic, "body", research)
    sections = [await intro, await body]

    # Control flow is deterministic
    return {"sections": sections}

@entrypoint()
async def review_workflow(topic: str) -> dict:
    """Entrypoint with human-in-the-loop."""
    draft = await generate_draft(topic)

    # interrupt() handled by workflow's on_interrupt callback
    review = interrupt({"document": draft, "action": "review"})

    return {"status": review["decision"], "document": draft}
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
        # Entrypoint runs in workflow, tasks become activities
        result = await app.ainvoke(topic)
        return result

@workflow.defn
class ReviewWorkflow:
    """Full control over Temporal features."""

    def __init__(self):
        self._resume_value = None

    @workflow.signal
    async def resume(self, value: dict) -> None:
        self._resume_value = value

    @workflow.query
    def get_status(self) -> dict:
        return {"waiting": self._waiting}

    @workflow.run
    async def run(self, topic: str) -> dict:
        app = compile("review_workflow")
        result = await app.ainvoke(
            topic,
            on_interrupt=self._handle_interrupt,
        )
        return result

    async def _handle_interrupt(self, value: dict) -> dict:
        self._waiting = True
        await workflow.wait_condition(lambda: self._resume_value is not None)
        self._waiting = False
        return self._resume_value
```

### 4. Register with Plugin

```python
# run_worker.py
from temporalio.contrib.langgraph import LangGraphFunctionalPlugin

# NO explicit task registration - discovered dynamically!
plugin = LangGraphFunctionalPlugin(
    entrypoints=[document_workflow, review_workflow],
    default_task_timeout=timedelta(minutes=10),
    task_options={
        "research_topic": {
            "start_to_close_timeout": timedelta(minutes=15),
        },
    },
)

# Plugin configures sandbox passthrough automatically
client = await Client.connect("localhost:7233", plugins=[plugin])

worker = Worker(
    client,
    task_queue="langgraph-functional",
    workflows=[DocumentWorkflow, ReviewWorkflow],
)
```

## Sample Structure

```
functional_api_proposal/
├── tasks.py          # @task functions (→ activities, can be non-deterministic)
├── entrypoint.py     # @entrypoint functions (→ run in workflow, must be deterministic)
├── workflow.py       # User-defined Temporal workflows
├── run_worker.py     # Plugin setup
├── run_workflow.py   # Execute workflows
└── README.md
```

## Running the Sample

```bash
# 1. Start Temporal
temporal server start-dev

# 2. Start Worker
python -m langgraph_plugin.functional_api.run_worker

# 3. Run Workflows
python -m langgraph_plugin.functional_api.run_workflow document
python -m langgraph_plugin.functional_api.run_workflow review
```

## Implementation Details

### Plugin Responsibilities

```python
class LangGraphFunctionalPlugin(SimplePlugin):
    def __init__(self, entrypoints, ...):
        # 1. Register entrypoints by name (extracted from __name__)
        for ep in entrypoints:
            register_entrypoint(ep.__name__, ep)

        # 2. Configure sandbox passthrough
        def workflow_runner(runner):
            return runner.with_passthrough_modules(
                "pydantic_core", "langchain_core",
                "annotated_types", "langgraph"
            )

        # 3. Provide dynamic task activity
        def add_activities(activities):
            return list(activities) + [execute_langgraph_task]

        # 4. Configure data converter
        super().__init__(
            workflow_runner=workflow_runner,
            activities=add_activities,
            data_converter=pydantic_converter,
        )
```

### CONFIG_KEY_CALL Injection

When `compile()` returns the runner, it injects a custom callback:

```python
def temporal_call_callback(func, args, retry_policy, ...):
    task_id = identifier(func)  # "mymodule.research_topic"

    # Schedule dynamic activity
    return workflow.execute_activity(
        execute_langgraph_task,
        args=(task_id, serialize(args)),
        start_to_close_timeout=get_timeout(task_id),
    )
```

### Dynamic Task Activity

```python
@activity.defn
async def execute_langgraph_task(task_id: str, args: bytes) -> bytes:
    """Execute any @task function by module path."""
    module_name, func_name = task_id.rsplit(".", 1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)

    result = await func(*deserialize(args))
    return serialize(result)
```

## Determinism Rules

### ✅ Allowed in @entrypoint (runs in workflow)
- Control flow: `if`, `for`, `while`, `match`
- Task calls: `await my_task(...)`
- Parallel tasks: `asyncio.gather(*[task1(), task2()])`
- `interrupt()` for human-in-the-loop
- Pure functions, data transformations

### ❌ Not allowed in @entrypoint (sandbox rejects)
- `time.time()`, `datetime.now()`
- `random.random()`, `uuid.uuid4()`
- Network I/O, file I/O
- Non-deterministic libraries

### ✅ Allowed in @task (runs as activity)
- Everything! Tasks are activities with no sandbox restrictions
- API calls, database access, file I/O
- Time, random, UUIDs
- Any non-deterministic operation

## Comparison with Graph API

| Aspect | Graph API | Functional API |
|--------|-----------|----------------|
| Definition | `StateGraph` + `add_node()` | `@task` + `@entrypoint` |
| Control flow | Graph edges | Python code |
| Execution context | Traversal in workflow, nodes as activities | Entrypoint in workflow, tasks as activities |
| In-workflow API | `compile("name")` | `compile("name")` |
| Activity discovery | From graph nodes | Dynamic via `CONFIG_KEY_CALL` |
| Registration | `graphs={name: builder}` | `entrypoints=[func, ...]` |
| Sandbox | Passthrough for langchain_core | + passthrough for langgraph |
