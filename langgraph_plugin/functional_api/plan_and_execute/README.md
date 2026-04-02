# Plan-and-Execute Agent (Functional API)

An agent that creates a structured plan and executes each step sequentially using available tools.

## Overview

The plan-and-execute pattern separates planning from execution:

1. **Plan** - Create a structured plan with specific steps
2. **Execute** - Run each step using appropriate tools
3. **Summarize** - Generate final response from results

## Architecture

```
User Objective
      │
      ▼
┌─────────────┐
│ create_plan │
│   (task)    │
└──────┬──────┘
       │
       ▼
   For each step:
       │
       ▼
┌──────────────┐
│ execute_step │ ──► Step 1 result
│   (task)     │
└──────────────┘
       │
       ▼
┌──────────────┐
│ execute_step │ ──► Step 2 result
│   (task)     │
└──────────────┘
       │
       ▼
      ...
       │
       ▼
┌───────────────────┐
│ generate_response │
│      (task)       │
└───────────────────┘
```

## Key Code

### Sequential Step Execution

```python
@entrypoint()
async def plan_execute_entrypoint(objective: str) -> dict:
    # Step 1: Create the plan
    plan = await create_plan(objective)

    # Step 2: Execute each step sequentially
    step_results = []
    for step in plan["steps"]:
        result = await execute_step(
            step_number=step["step_number"],
            description=step["description"],
            tool_hint=step["tool_hint"],
        )
        step_results.append(result)

    # Step 3: Generate final response
    final_response = await generate_response(objective, step_results)

    return {
        "objective": objective,
        "plan": plan,
        "step_results": step_results,
        "final_response": final_response,
    }
```

### Structured Plan

```python
@task
def create_plan(objective: str) -> dict:
    """Generate a structured plan with steps."""
    return {
        "objective": objective,
        "steps": [
            {"step_number": 1, "description": "...", "tool_hint": "search"},
            {"step_number": 2, "description": "...", "tool_hint": "calculate"},
            {"step_number": 3, "description": "...", "tool_hint": "analyze"},
        ]
    }
```

## Why Temporal?

- **Step durability**: Each step execution is durable
- **Progress visibility**: See plan and completed steps in UI
- **Partial completion**: Resume from last completed step
- **Audit trail**: Full execution history preserved

## Running the Sample

1. Start Temporal:
   ```bash
   temporal server start-dev
   ```

2. Run with API key:
   ```bash
   export OPENAI_API_KEY=your-key
   uv run langgraph_plugin/functional_api/plan_and_execute/run_worker.py
   ```

3. Execute an objective:
   ```bash
   uv run langgraph_plugin/functional_api/plan_and_execute/run_workflow.py
   ```

## Customization

### Add Re-planning

```python
@entrypoint()
async def plan_execute_entrypoint(objective: str) -> dict:
    plan = await create_plan(objective)
    step_results = []

    for step in plan["steps"]:
        result = await execute_step(step)
        step_results.append(result)

        # Re-plan if step failed
        if not result["success"]:
            plan = await replan(objective, step_results)
```

### Parallel Step Execution

```python
# For independent steps, execute in parallel
independent_steps = [s for s in plan["steps"] if s["can_parallelize"]]
futures = [execute_step(s) for s in independent_steps]
results = [await f for f in futures]
```
