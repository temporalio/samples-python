"""A Deep Agent whose durable execution is also traced to LangSmith.

The workflow itself is an ordinary Deep Agent — the tracing comes entirely from
composing ``LangSmithPlugin`` alongside ``DeepAgentsPlugin`` on the client (see
``main.py``). The plugin carries no tracing context of its own; the observability
plugin captures the LLM calls that ``DeepAgentsPlugin`` runs as activities.
"""

# @@@SNIPSTART python-deepagents-langsmith-tracing-workflow
from deepagents import create_deep_agent
from temporalio import workflow


@workflow.defn
class TracedAgent:
    @workflow.run
    async def run(self, question: str) -> str:
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-5",
            system_prompt="You are a helpful assistant.",
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        return result["messages"][-1].content


# @@@SNIPEND
