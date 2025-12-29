# Supervisor Multi-Agent System

A supervisor agent that coordinates specialized worker agents (researcher, writer, analyst) using LangGraph with Temporal for durable execution.

## What This Sample Demonstrates

- **Multi-agent orchestration**: A supervisor coordinates multiple specialized agents
- **Task routing**: The supervisor intelligently routes tasks to the appropriate agent
- **Agent specialization**: Each agent has specific tools and expertise
- **Durable multi-agent execution**: All agent interactions run as Temporal activities
- **Crash recovery**: If any agent fails or the worker crashes, execution resumes seamlessly

## How It Works

### Architecture

```
                    ┌─────────────┐
                    │  Supervisor │
                    │ (Coordinator)│
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ Researcher │  │   Writer   │  │  Analyst   │
    │            │  │            │  │            │
    │ web_search │  │write_content│ │ calculate  │
    │            │  │ summarize  │  │analyze_data│
    └────────────┘  └────────────┘  └────────────┘
```

### Agents

1. **Supervisor**: Central coordinator that analyzes requests, decides which agent(s) to use, routes tasks, and synthesizes final responses

2. **Researcher**: Specialized in information gathering with web search capabilities. Use for research tasks, fact-finding, and current events

3. **Writer**: Specialized in content creation and summarization. Use for writing articles, reports, summaries, or any content generation

4. **Analyst**: Specialized in calculations and data analysis. Use for math problems, data interpretation, or analytical tasks

### Flow

1. User sends a request to the supervisor
2. Supervisor analyzes the request and determines which agent(s) are needed
3. Supervisor routes the task to the appropriate agent
4. Agent completes its work and returns results to supervisor
5. Supervisor may route to additional agents or synthesize final response
6. Final response is returned to the user

### Temporal Integration

With Temporal, the multi-agent system gains:
- **Durability**: Each agent's execution is checkpointed
- **Retries**: Failed agent calls are automatically retried
- **Recovery**: If the worker crashes, execution resumes from the last completed agent interaction
- **Visibility**: Track agent interactions through Temporal's UI

## Prerequisites

- Temporal server running locally (`temporal server start-dev`)
- OpenAI API key set: `export OPENAI_API_KEY=your-key`
- Install dependencies: `uv sync --group langgraph`

## Running the Example

First, start the worker:
```bash
uv run langgraph_samples/multi_agent/supervisor/run_worker.py
```

Then, in a separate terminal, run the workflow:
```bash
uv run langgraph_samples/multi_agent/supervisor/run_workflow.py
```

## Expected Output

The supervisor will coordinate the agents to:
1. Use the researcher to find AI trends information
2. Use the analyst to evaluate which trends are most impactful
3. Use the writer to create an executive summary

You'll see the final synthesized response incorporating work from multiple agents.

## Example Queries

The default query demonstrates multi-agent collaboration:
```
Research the latest AI trends in 2024, analyze which trends are most
impactful for enterprise software development, and write a brief
executive summary (2-3 paragraphs).
```

You can modify `run_workflow.py` to test different scenarios:

- **Research only**: "What are the key features of Temporal workflows?"
- **Analysis only**: "Calculate the compound interest on $10,000 at 5% for 3 years"
- **Writing only**: "Write a brief introduction to LangGraph multi-agent systems"
- **Multi-agent**: "Research LangGraph patterns, analyze their trade-offs, and summarize recommendations"

## Key Files

- `graph.py`: Defines the supervisor and specialized agents using `langgraph-supervisor`
- `workflow.py`: Temporal workflow that executes the multi-agent system
- `run_worker.py`: Starts the Temporal worker with the LangGraph plugin
- `run_workflow.py`: Executes the workflow with a sample request

## References

- [LangGraph Supervisor Library](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Multi-Agent Systems in LangGraph](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [Temporal LangGraph Integration](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/langgraph/README.md)
