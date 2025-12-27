# ReAct Agent with Tools

A ReAct (Reasoning + Acting) agent using LangGraph's `create_react_agent` with Temporal-wrapped tools for durable execution.

## What This Sample Demonstrates

- **ReAct pattern**: The think-act-observe loop where the LLM decides actions and observes results
- **Durable tool execution**: Using `temporal_tool()` to wrap LangChain tools as Temporal activities
- **Automatic retries**: Each tool invocation has its own timeout and retry policy
- **Cyclic graph execution**: The agent loops between thinking and acting until it has an answer

## How It Works

1. **Tools**: Three LangChain tools (`get_weather`, `calculate`, `search_knowledge`) simulate external APIs
2. **Temporal wrapping**: Each tool is wrapped with `temporal_tool()` for durable execution
3. **ReAct agent**: `create_react_agent()` builds a cyclic graph that alternates between LLM calls and tool execution
4. **Workflow**: Invokes the agent and returns the final conversation state

The ReAct pattern:
```
User Query → [Think] → [Act (tool)] → [Observe] → [Think] → ... → Final Answer
```

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
