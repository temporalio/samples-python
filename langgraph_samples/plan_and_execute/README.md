# Plan-and-Execute Agent

An agent that separates planning from execution, creating a high-level plan first and then executing each step sequentially with the ability to replan based on results.

## Overview

The Plan-and-Execute pattern:
1. **Planning phase** - Analyzes the objective and creates a step-by-step plan
2. **Execution phase** - Runs each step using available tools
3. **Evaluation** - Checks progress after each step
4. **Replanning** - Adjusts the plan if steps fail or new information emerges
5. **Response** - Synthesizes results into a final answer

## Why This Pattern?

Plan-and-Execute offers advantages over pure ReAct:
- **Structured approach**: Clear separation of thinking and doing
- **Visibility**: The plan is visible before execution starts
- **Resumability**: Temporal can resume from any step
- **Adaptability**: Dynamic replanning when things change

## Architecture

```
[Plan] --> [Execute Step 1] --> [Evaluate] --> [Execute Step 2] --> ...
                                    |
                                    v
                               [Replan?] --> [New Plan] --> [Execute] --> ...
                                    |
                                    v
                               [Respond] --> END
```

Each step runs as a Temporal activity with its own retry logic.

## Available Tools

The executor agent has access to:
- `calculate`: Evaluate mathematical expressions
- `lookup`: Retrieve information about topics
- `analyze`: Analyze data or text

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
   uv run langgraph_samples/plan_and_execute/run_worker.py
   ```

3. In another terminal, run the workflow:
   ```bash
   uv run langgraph_samples/plan_and_execute/run_workflow.py
   ```

## Sample Output

```
============================================================
EXECUTION RESULT
============================================================

Steps Executed:
  1. Look up information about LangGraph
     Result: LangGraph is a library for building stateful, multi-actor LLM applications...
  2. Look up information about other agent frameworks
     Result: AI agents are autonomous systems that use LLMs...
  3. Calculate the feature comparison
     Result: Result: 5...

Final Answer:
LangGraph is a library for building stateful, multi-actor LLM applications with
support for cycles, branches, and persistence. Compared to a basic ReAct agent,
LangGraph offers 5 additional key features: state persistence, human-in-the-loop
support, parallel execution, conditional branching, and streaming...
```

## Key Features Demonstrated

### 1. Plan Generation
```python
class Plan(BaseModel):
    objective: str
    steps: list[PlanStep]

# LLM generates structured plan
planner = prompt | model.with_structured_output(Plan)
plan = planner.invoke({"objective": objective})
```

### 2. Step-by-Step Execution
```python
def execute_step(state: PlanExecuteState) -> dict[str, Any]:
    step = plan.steps[current_step]
    result = executor_agent.invoke({"messages": [HumanMessage(step.description)]})
    return {"step_results": [...], "current_step": current_step + 1}
```

### 3. Dynamic Routing
```python
def should_continue(state) -> Literal["execute", "replan", "respond"]:
    if state.get("needs_replan"):
        return "replan"
    if current_step < len(plan.steps):
        return "execute"
    return "respond"
```

### 4. Replanning
```python
def replan(state: PlanExecuteState) -> dict[str, Any]:
    # Consider what's been done and create new steps
    new_plan = replanner.invoke({
        "objective": objective,
        "completed": completed_work
    })
    return {"plan": new_plan, "current_step": 0}
```

## Customization

### Adding Custom Tools

```python
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    # Implement actual web search
    pass

tools = [calculate, lookup, analyze, search_web]
executor_agent = create_agent(model, tools)
```

### Adjusting Plan Constraints

Modify the planner prompt to control plan characteristics:

```python
plan_prompt = ChatPromptTemplate.from_messages([
    ("system", "Create a plan with 3-5 specific steps. Each step should take 1-2 minutes to execute..."),
    ...
])
```

## Comparison with ReAct

| Aspect | ReAct | Plan-and-Execute |
|--------|-------|------------------|
| Approach | Think-act in each iteration | Plan all steps, then execute |
| Visibility | Actions emerge dynamically | Full plan visible upfront |
| Control | Less predictable | More structured |
| Flexibility | High adaptability | Requires explicit replanning |
| Best for | Exploratory tasks | Well-defined objectives |

## Next Steps

- Add more sophisticated tools (web search, code execution)
- Implement plan approval (human-in-the-loop before execution)
- Add parallel step execution for independent steps
- Implement plan caching for similar objectives
