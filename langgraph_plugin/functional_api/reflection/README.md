# Reflection Agent (Functional API)

An agent that generates content, critiques it, and iteratively improves until quality criteria are met.

## Overview

The reflection pattern implements a generate-critique-revise loop:

1. **Generate** - Create initial content
2. **Critique** - Evaluate with structured feedback
3. **Revise** - Improve based on critique
4. **Loop** - Repeat until satisfactory or max iterations

## Architecture

```
┌──────────────────┐
│ generate_content │
│     (task)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ critique_content │◄────┐
│     (task)       │     │
└────────┬─────────┘     │
         │               │
         ▼               │
    Satisfactory?        │
         │               │
    NO   │    YES        │
         │     └──► Return Final
         ▼               │
┌──────────────────┐     │
│  revise_content  │─────┘
│     (task)       │
└──────────────────┘
```

## Key Code

### Entrypoint with Iteration Loop

```python
@entrypoint()
async def reflection_entrypoint(task_description: str, max_iterations: int = 3) -> dict:
    # Generate initial draft
    current_draft = await generate_content(task_description)
    critiques = []

    for iteration in range(1, max_iterations + 1):
        # Critique current draft
        critique = await critique_content(task_description, current_draft, iteration)
        critiques.append(critique)

        # Check if good enough
        if critique.get("is_satisfactory"):
            return {"final_content": current_draft, "status": "satisfactory"}

        # Revise based on feedback
        current_draft = await revise_content(task_description, current_draft, critique)

    return {"final_content": current_draft, "status": "max_iterations_reached"}
```

### Structured Critique

```python
@task
def critique_content(task: str, draft: str, iteration: int) -> dict:
    """Returns structured critique with score and suggestions."""
    return {
        "strengths": [...],
        "weaknesses": [...],
        "suggestions": [...],
        "quality_score": 7,
        "is_satisfactory": True  # score >= threshold
    }
```

## Why Temporal?

- **Durability**: Multi-iteration refinement completes reliably
- **Visibility**: See each critique/revision in workflow history
- **Cost tracking**: Monitor LLM calls across iterations
- **Resume**: Continue from any iteration if interrupted

## Running the Sample

1. Start Temporal:
   ```bash
   temporal server start-dev
   ```

2. Run with API key:
   ```bash
   export OPENAI_API_KEY=your-key
   uv run langgraph_plugin/functional_api/reflection/run_worker.py
   ```

3. Execute:
   ```bash
   uv run langgraph_plugin/functional_api/reflection/run_workflow.py
   ```

## Customization

### Adjust Quality Threshold

```python
# In critique task, change when content is "satisfactory"
is_satisfactory = quality_score >= 8  # Stricter threshold
```

### Add Domain-Specific Criteria

```python
@task
def critique_content(task: str, draft: str, iteration: int) -> dict:
    # Add custom evaluation criteria
    criteria = ["technical accuracy", "code correctness", "SEO optimization"]
    ...
```
