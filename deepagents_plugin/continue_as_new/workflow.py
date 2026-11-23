"""Long-running research agent that carries state across continue-as-new.

A long conversation would bloat workflow history until it hits Temporal's limit.
``run_deep_agent(agent, input, state_snapshot=...)`` solves this: once a turn
finishes with pending todos and the server recommends continuing
(``workflow.info().is_continue_as_new_suggested()`` — the default and
recommended mode, accounting for both history length and size), it snapshots the
accumulated messages and the agent's state files and continues into a fresh
run. Pass ``continue_as_new_after=N`` instead to trigger on a fixed
history-event count.

``run_deep_agent`` reads the todos that LangChain's ``TodoListMiddleware``
writes. ``create_deep_agent`` does not add that middleware, so the agent here
adds it; without it, the run returns after each turn and never continues as
new.

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
from langchain.agents.middleware import TodoListMiddleware
from temporalio import workflow
from temporalio.deepagents import run_deep_agent


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
            # run_deep_agent continues as new only while todos are pending, and
            # this middleware is what records them.
            middleware=[TodoListMiddleware()],
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
