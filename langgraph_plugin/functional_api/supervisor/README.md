# Supervisor Multi-Agent (Functional API)

A supervisor agent that coordinates multiple specialized agents to complete complex tasks.

## Overview

The supervisor pattern uses a central coordinator:

1. **Supervisor** - Decides which agent should work next
2. **Researcher** - Gathers information
3. **Writer** - Creates content
4. **Analyst** - Performs calculations and analysis
5. **Loop** - Continue until supervisor says FINISH

## Architecture

```
User Query
      │
      ▼
┌───────────────────┐
│ supervisor_decide │◄──────────────────┐
│      (task)       │                   │
└─────────┬─────────┘                   │
          │                             │
          ▼                             │
    Route to agent                      │
          │                             │
    ┌─────┼─────┬─────────┐             │
    │     │     │         │             │
    ▼     ▼     ▼         ▼             │
┌──────┐┌──────┐┌───────┐ FINISH        │
│研究者││作家  ││分析师 │    │          │
│(task)││(task)││(task) │    │          │
└──┬───┘└──┬───┘└───┬───┘    │          │
   │       │        │        │          │
   └───────┴────────┴────────┴──────────┘
                             │
                             ▼
                      Final Summary
```

## Key Code

### Supervisor Loop

```python
@entrypoint()
async def supervisor_entrypoint(query: str, max_iterations: int = 10) -> dict:
    available_agents = ["researcher", "writer", "analyst"]
    messages = [{"role": "user", "content": query}]
    agent_outputs = []

    for iteration in range(max_iterations):
        # Supervisor decides next step
        decision = await supervisor_decide(messages, available_agents)
        next_agent = decision["next_agent"]

        if next_agent == "FINISH":
            break

        # Route to appropriate agent
        if next_agent == "researcher":
            output = await researcher_work(decision["task_for_agent"])
        elif next_agent == "writer":
            output = await writer_work(decision["task_for_agent"], context)
        elif next_agent == "analyst":
            output = await analyst_work(decision["task_for_agent"], context)

        agent_outputs.append(output)
        messages.append({"role": next_agent, "content": output})

    # Final summary
    final_answer = await writer_work("Summarize the work done", all_outputs)
    return {"final_answer": final_answer, "agent_outputs": agent_outputs}
```

### Agent Tasks

```python
@task
def supervisor_decide(messages: list, available_agents: list) -> dict:
    """Decide which agent should work next."""
    return {"next_agent": "researcher", "task_for_agent": "Find data on..."}

@task
def researcher_work(task: str) -> str:
    """Gather information on the given task."""
    return search_and_summarize(task)

@task
def writer_work(task: str, context: str) -> str:
    """Create content based on task and context."""
    return generate_content(task, context)
```

## Why Temporal?

- **Agent coordination**: Reliable handoffs between agents
- **Visibility**: See each agent's contribution
- **Long-running**: Complex tasks with many agents complete reliably
- **Audit trail**: Full conversation history preserved

## Running the Sample

1. Start Temporal:
   ```bash
   temporal server start-dev
   ```

2. Run with API key:
   ```bash
   export OPENAI_API_KEY=your-key
   uv run langgraph_plugin/functional_api/supervisor/run_worker.py
   ```

3. Submit a complex task:
   ```bash
   uv run langgraph_plugin/functional_api/supervisor/run_workflow.py
   ```

## Customization

### Add More Agents

```python
available_agents = ["researcher", "writer", "analyst", "coder", "reviewer"]

# In the routing logic:
elif next_agent == "coder":
    output = await coder_work(decision["task_for_agent"], context)
```

### Parallel Agent Execution

```python
# For independent agent tasks
if decision["parallel_agents"]:
    futures = [agent_work(agent, task) for agent, task in decision["parallel_agents"]]
    outputs = [await f for f in futures]
```
