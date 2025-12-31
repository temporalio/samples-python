# Human-in-the-Loop Samples

Two approaches to implementing human-in-the-loop approval workflows with LangGraph and Temporal.

## Samples

### [approval_graph_interrupt](./approval_graph_interrupt/)

Uses LangGraph's `interrupt()` function to pause graph execution.

- Graph calls `interrupt(request_data)` to pause
- Workflow detects `__interrupt__` in result, waits for signal
- Workflow resumes graph with `Command(resume=response)`

**Best for:** Standard LangGraph patterns, portable graph definitions.

### [approval_wait_condition](./approval_wait_condition/)

Uses `run_in_workflow=True` to access Temporal operations directly in graph nodes.

- Node marked with `metadata={"run_in_workflow": True}`
- Node uses `workflow.instance()` to access workflow
- Node waits directly with `workflow.wait_condition()`

**Best for:** Keeping all wait logic encapsulated in the graph, simpler workflow code.

## Quick Comparison

| Aspect | graph_interrupt | wait_condition |
|--------|-----------------|----------------|
| Wait logic location | Workflow | Graph node |
| Graph portability | Higher | Lower |
| Workflow complexity | More code | Less code |
| Temporal API access | Indirect | Direct |
