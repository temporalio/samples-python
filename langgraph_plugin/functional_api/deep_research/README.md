# Deep Research Agent (Functional API)

A multi-step research agent that plans queries, executes parallel searches, and synthesizes findings into a comprehensive report.

## Overview

The deep research pattern:

1. **Plan** - Generate research queries based on topic
2. **Search** - Execute searches in parallel
3. **Evaluate** - Check if results are sufficient
4. **Iterate** - Refine and search again if needed
5. **Synthesize** - Create final report

## Architecture

```
Research Topic
      │
      ▼
┌──────────────┐
│ plan_research│
│    (task)    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│     execute_search (task)    │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐│  ← Parallel execution
│  │ Q1 │ │ Q2 │ │ Q3 │ │ Q4 ││
│  └────┘ └────┘ └────┘ └────┘│
└──────────────┬───────────────┘
               │
               ▼
        Enough results?
               │
          NO   │   YES
               │    │
        ┌──────┘    │
        │           ▼
        │    ┌──────────────────┐
        │    │ synthesize_report│
        │    │      (task)      │
        │    └──────────────────┘
        │
        └──► Plan more queries...
```

## Key Code

### Parallel Search Execution

```python
@entrypoint()
async def deep_research_entrypoint(topic: str, max_iterations: int = 2) -> dict:
    all_results = []

    for iteration in range(1, max_iterations + 1):
        # Plan research queries
        queries = await plan_research(topic)

        # Execute searches IN PARALLEL
        search_futures = [execute_search(q["query"], q["purpose"]) for q in queries]
        search_results = [await future for future in search_futures]
        all_results.extend(search_results)

        # Check if we have enough relevant results
        relevant_count = sum(1 for r in search_results if r.get("relevant"))
        if relevant_count >= 2:
            break

    # Synthesize final report
    report = await synthesize_report(topic, all_results)
    return {"report": report, "total_searches": len(all_results)}
```

### Parallel Pattern

```python
# Start all tasks concurrently (non-blocking)
futures = [execute_search(q) for q in queries]

# Wait for all to complete
results = [await f for f in futures]
```

This is the key difference from Graph API - parallel execution uses simple Python patterns.

## Why Temporal?

- **Parallel durability**: All concurrent searches complete reliably
- **Cost efficiency**: Parallel execution reduces total time
- **Progress tracking**: See individual search completions
- **Resume**: Continue from last completed search if interrupted

## Running the Sample

1. Start Temporal:
   ```bash
   temporal server start-dev
   ```

2. Run with API key:
   ```bash
   export OPENAI_API_KEY=your-key
   uv run langgraph_plugin/functional_api/deep_research/run_worker.py
   ```

3. Research a topic:
   ```bash
   uv run langgraph_plugin/functional_api/deep_research/run_workflow.py
   ```

## Customization

### Adjust Search Breadth

```python
@task
def plan_research(topic: str) -> list[dict]:
    # Generate more or fewer queries
    return generate_queries(topic, count=6)  # Default might be 4
```

### Add Source Filtering

```python
@task
def execute_search(query: str, purpose: str) -> dict:
    # Filter to specific sources
    results = search(query, sources=["academic", "news"])
    ...
```
