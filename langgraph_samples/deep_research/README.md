# Deep Research Agent

A multi-step research agent that performs iterative research using real web search to produce comprehensive reports. This sample demonstrates how Temporal's durable execution enables long-running research workflows with LangGraph's parallel execution.

## Overview

The Deep Research Agent:
1. **Plans research** - Analyzes the topic and generates targeted search queries using OpenAI
2. **Parallel search** - Executes multiple DuckDuckGo web searches concurrently using LangGraph's Send API
3. **Evaluates results** - Grades search results for relevance and coverage
4. **Iterates** - Continues researching if more information is needed
5. **Synthesizes** - Produces a comprehensive research report using OpenAI

## Why Temporal?

Research workflows are ideal for Temporal because:
- **Long-running**: Research can take minutes to hours
- **Parallel execution**: Multiple web searches run as separate activities
- **Fault tolerance**: If a search fails, only that activity retries
- **Visibility**: Progress is tracked in Temporal's UI
- **Resumable**: Interrupted research continues where it left off

## Architecture

```
[Plan] --> [Search 1] -\
       --> [Search 2] ----> [Evaluate] --> [Synthesize] --> END
       --> [Search 3] -/         |
                                 v
                            [Continue?]
                                 |
                           [More Plan] --> ...
```

Each search runs as a separate Temporal activity, enabling parallel execution.

## Running the Sample

### Prerequisites

- Temporal server running locally
- OpenAI API key

### Steps

1. Start the Temporal server:
   ```bash
   temporal server start-dev
   ```

2. In one terminal, start the worker:
   ```bash
   export OPENAI_API_KEY=your-key-here
   uv run langgraph_samples/rag/deep_research/run_worker.py
   ```

3. In another terminal, run the workflow:
   ```bash
   uv run langgraph_samples/rag/deep_research/run_workflow.py
   ```

## Sample Output

```
============================================================
RESEARCH REPORT
============================================================

## Executive Summary
LangGraph and Temporal combine to create durable AI agents that survive
failures and can handle long-running workflows...

## Main Findings
### Core Concepts
- LangGraph provides the agent graph structure
- Temporal provides durable execution...

### Integration Benefits
- Each graph node runs as a Temporal activity
- Automatic retries for failed operations...

## Conclusions
The LangGraph-Temporal integration is ideal for production AI agents...
```

## Key Features Demonstrated

### 1. Parallel Search with Send API
```python
def fan_out_searches(state: ResearchState) -> list[Send]:
    """Fan out to parallel search executions."""
    return [
        Send("search", {"query": q.query, "purpose": q.purpose})
        for q in state.get("search_queries", [])
    ]
```

### 2. Research Iteration Loop
```python
def should_continue(state: ResearchState) -> Literal["synthesize", "plan"]:
    """Decide whether to continue researching."""
    if iteration < max_iterations and coverage < threshold:
        return "plan"  # Continue researching
    return "synthesize"  # Ready to report
```

### 3. Result Aggregation
Results from parallel searches are aggregated using a reducer:
```python
search_results: Annotated[list[SearchResult], lambda x, y: x + y]
```

## Customization

### Using Alternative Search APIs

The sample uses DuckDuckGo by default. To use other search providers:

```python
# Tavily (requires TAVILY_API_KEY)
from langchain_community.tools import TavilySearchResults
search_tool = TavilySearchResults()

# Or use any LangChain-compatible search tool
```

### Adjusting Research Depth

Control iteration depth when starting the workflow:

```python
result = await client.execute_workflow(
    DeepResearchWorkflow.run,
    args=["Your research topic", 3],  # max 3 iterations
    ...
)
```

## Next Steps

- Integrate additional search providers (Tavily, Exa, Google)
- Implement continue-as-new for very long research sessions
- Add human review checkpoints for important findings
- Store research artifacts in Temporal's data store
