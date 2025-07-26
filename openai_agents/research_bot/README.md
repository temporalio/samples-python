# Research Bot

Multi-agent research system with specialized roles, extended with Temporal's durable execution.

*Adapted from [OpenAI Agents SDK research bot](https://github.com/openai/openai-agents-python/tree/main/examples/research_bot)*

## Architecture

The flow is:

1. User enters their research topic
2. `planner_agent` comes up with a plan to search the web for information. The plan is a list of search queries, with a search term and a reason for each query.
3. For each search item, we run a `search_agent`, which uses the Web Search tool to search for that term and summarize the results. These all run in parallel.
4. Finally, the `writer_agent` receives the search summaries, and creates a written report.

## Running the Example

First, start the worker:
```bash
uv run openai_agents/research_bot/run_worker.py
```

Then run the research workflow:
```bash
uv run openai_agents/research_bot/run_research_workflow.py
```

## Suggested Improvements

If you're building your own research bot, some ideas to add to this are:

1. Retrieval: Add support for fetching relevant information from a vector store. You could use the File Search tool for this.
2. Image and file upload: Allow users to attach PDFs or other files, as baseline context for the research.
3. More planning and thinking: Models often produce better results given more time to think. Improve the planning process to come up with a better plan, and add an evaluation step so that the model can choose to improve its results, search for more stuff, etc.
4. Code execution: Allow running code, which is useful for data analysis.