# ReAct Agent with Tools

A ReAct (Reasoning + Acting) agent using LangChain's `create_agent` with Temporal for durable execution.

## What This Sample Demonstrates

- **ReAct pattern**: The think-act-observe loop where the LLM decides actions and observes results
- **Durable execution**: Each graph node runs as a Temporal activity with automatic retries
- **Crash recovery**: If the worker fails, execution resumes from the last completed node
- **Cyclic graph execution**: The agent loops between thinking and acting until it has an answer

## How It Works

1. **Tools**: Three LangChain tools (`get_weather`, `calculate`, `search_knowledge`) simulate external APIs
2. **Agent**: `create_agent()` builds a cyclic graph with "agent" and "tools" nodes
3. **Temporal integration**: Each node runs as a separate activity, providing durability
4. **Workflow**: Invokes the agent and returns the final conversation state

The ReAct pattern:
```
User Query → [Agent Node] → [Tools Node] → [Agent Node] → ... → Final Answer
```

Each node execution is:
- **Durable**: Progress is saved after each node completes
- **Retryable**: Failed nodes can be automatically retried
- **Recoverable**: If the worker crashes, execution resumes from the last completed node

## Prerequisites

- Temporal server running locally (`temporal server start-dev`)
- OpenAI API key set: `export OPENAI_API_KEY=your-key`

## Running the Example

First, start the worker:
```bash
uv run langgraph_samples/basic/react_agent/run_worker.py
```

Then, in a separate terminal, run the workflow:
```bash
uv run langgraph_samples/basic/react_agent/run_workflow.py
```

## Expected Output

```
The weather in Tokyo is currently 68°F with clear skies.
```

You can modify the query in `run_workflow.py` to test different tools:
- **Weather tool**: "What's the weather like in Tokyo?"
- **Calculator tool**: "What is 25 * 4 + 10?"
- **Knowledge search**: "Tell me about Temporal and LangGraph"
