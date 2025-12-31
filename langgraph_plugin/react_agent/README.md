# ReAct Agent with Tools

A ReAct (Reasoning + Acting) agent using LangChain's `create_agent` with Temporal for durable execution.

## What This Sample Demonstrates

- **ReAct pattern**: The think-act-observe loop where the LLM decides actions and observes results
- **Multi-step reasoning**: The agent makes multiple tool calls to gather information and compute results
- **Durable execution**: Each graph node runs as a Temporal activity with automatic retries
- **Crash recovery**: If the worker fails, execution resumes from the last completed node
- **Cyclic graph execution**: The agent loops between thinking and acting until it has an answer

## How It Works

1. **Tools**: Two LangChain tools (`get_weather`, `calculate`) provide weather data and math operations
2. **Agent**: `create_agent()` builds a cyclic graph with "agent" and "tools" nodes
3. **Temporal integration**: Each node runs as a separate activity, providing durability
4. **Workflow**: Invokes the agent and returns the final conversation state

The ReAct pattern:
```
User Query → [Agent Node] → [Tools Node] → [Agent Node] → [Tools Node] → ... → Final Answer
```

The sample query "What's the weather in Tokyo? Convert the temperature to Celsius." demonstrates multiple agentic loops:
1. Agent decides to call `get_weather("Tokyo")` → gets "68°F, Clear skies"
2. Agent decides to call `calculate("(68-32)*5/9")` → gets the Celsius conversion
3. Agent synthesizes final answer

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
uv run langgraph_plugin/react_agent/run_worker.py
```

Then, in a separate terminal, run the workflow:
```bash
uv run langgraph_plugin/react_agent/run_workflow.py
```

## Expected Output

```
The weather in Tokyo is 68°F (20°C) with clear skies.
```

You can modify the query in `run_workflow.py` to test different scenarios:
- **Weather only**: "What's the weather like in Paris?"
- **Calculator only**: "What is 25 * 4 + 10?"
- **Multi-step**: "What's the weather in New York and London? Which city is warmer?"
