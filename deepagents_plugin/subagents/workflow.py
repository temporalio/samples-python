"""Durability propagates across the whole agent tree — no per-sub-agent wiring.

A coordinator built with ``create_deep_agent(..., subagents=[...])`` delegates to
its sub-agents via the built-in ``task`` tool. Deep Agents builds each sub-agent
as a separate graph, but they inherit the parent's ``model`` object by default.
Because the plugin makes that model object durable (each generation is a
``deepagents.invoke_model`` activity), every sub-agent's model call is
automatically durable too — you wire the plugin once and the whole tree is
covered.

Here the coordinator delegates deep investigation to a ``researcher`` sub-agent
and then synthesizes a final answer; both the coordinator's and the researcher's
model calls run as activities.
"""

# @@@SNIPSTART python-deepagents-subagents-workflow
from deepagents import create_deep_agent
from temporalio import workflow


@workflow.defn
class SubagentsWorkflow:
    @workflow.run
    async def run(self, question: str) -> str:
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-5",
            system_prompt=(
                "You are a research coordinator. Delegate deep investigation to "
                "the researcher sub-agent via the task tool, then synthesize a "
                "final answer."
            ),
            subagents=[
                {
                    "name": "researcher",
                    "description": "Researches a topic in depth and reports findings.",
                    "system_prompt": "You research topics thoroughly and report back.",
                }
            ],
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        return result["messages"][-1].content


# @@@SNIPEND
