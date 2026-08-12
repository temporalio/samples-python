"""Long-running research agent that carries state across continue-as-new.

A long conversation would bloat workflow history until it hits Temporal's limit.
``run_deep_agent(agent, input, state_snapshot=...)`` solves this: once a turn
finishes with pending work and the server recommends continuing
(``workflow.info().is_continue_as_new_suggested()`` — the default and
recommended mode, accounting for both history length and size), it snapshots the
accumulated messages **and** the model/tool result cache and continues into a
fresh run — so completed model/tool calls are reused, not re-run, after the
continue-as-new. Pass ``continue_as_new_after=N`` instead to trigger on a fixed
history-event count.

The contract ``run_deep_agent`` requires is that the ``@workflow.run`` method
accepts the carried state, i.e. its signature is
``run(self, input, state_snapshot=None)`` where ``input`` is the messages
mapping. On a continue-as-new, ``run_deep_agent`` re-invokes the workflow with
``args=[input, snapshot]``, so ``input`` must be passed straight through — not
re-wrapped — or the carried conversation is corrupted. Only an in-workflow
``InMemorySaver`` (the default) is replay-safe; a durable checkpointer would do
I/O from workflow code.
"""

# @@@SNIPSTART python-deepagents-continue-as-new-workflow
from typing import Any

from deepagents import create_deep_agent
from temporalio import workflow
from temporalio.contrib.deepagents import run_deep_agent


@workflow.defn
class LongResearchAgent:
    @workflow.run
    async def run(
        self, input: dict[str, Any], state_snapshot: dict | None = None
    ) -> str:
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-5",
            system_prompt=(
                "You are a research agent. Break large tasks into todos and work "
                "through them until the research is complete."
            ),
        )
        result = await run_deep_agent(
            agent,
            # ``input`` is the messages mapping. Pass it through unchanged: on a
            # continue-as-new, run_deep_agent re-invokes this method with the
            # carried input as its first arg, so re-wrapping it here would nest a
            # dict where a message is expected and corrupt the conversation.
            input,
            # No threshold: continue-as-new fires when the agent still has
            # pending todos and the server suggests continuing — the recommended
            # mode. Pass continue_as_new_after=N to use a fixed event count.
            state_snapshot=state_snapshot,
        )
        return result["messages"][-1].content


# @@@SNIPEND
