"""Minimal single-shot Deep Agent, made durable by the plugin.

The workflow builds a vanilla ``create_deep_agent(...)`` and drives it with
``await agent.ainvoke(...)`` — exactly the code you would write outside Temporal.
The only reason it is durable is that a ``DeepAgentsPlugin`` is wired onto the
client (see ``run_worker.py``): the bare ``model="anthropic:..."`` string is
auto-routed through the ``deepagents.invoke_model`` activity, so the LLM call
gets Temporal-managed retries and timeouts while the agent's control loop
replays deterministically in the workflow.
"""

# @@@SNIPSTART python-deepagents-hello-world-workflow
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from deepagents import create_deep_agent


@workflow.defn
class HelloWorldAgent:
    @workflow.run
    async def run(self, question: str) -> str:
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-5",
            system_prompt="You are a helpful assistant. Answer concisely.",
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        return result["messages"][-1].content


# @@@SNIPEND
