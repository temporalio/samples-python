"""Human-in-the-loop: the native LangGraph interrupt mapped to Query + Update.

``create_deep_agent(..., interrupt_on=...)`` makes the agent pause before a
guarded tool runs. With an in-workflow ``InMemorySaver`` checkpointer, LangGraph
does *not* raise out of ``ainvoke`` — it returns the current state with an
``__interrupt__`` entry describing the pending approval. Because the agent loop
runs in the workflow, that pause surfaces directly in workflow code.

The plugin adds no shim here. The recommended Temporal mapping is:

* expose the pending approval via a ``@workflow.query`` so a client can read it;
* resume via a ``@workflow.update`` that feeds the human's decision back with the
  native ``Command(resume={"decisions": [...]})`` protocol; its validator rejects
  unsupported decisions before they are accepted into workflow history.

The ``InMemorySaver`` is replay-safe because its state lives in the workflow's
own memory (rehydrated by deterministic replay); the ``thread_id`` is the stable
workflow id.
"""

# @@@SNIPSTART python-deepagents-human-in-the-loop-workflow
from datetime import timedelta

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from temporalio import workflow
from temporalio.contrib.deepagents import tool_as_activity


@workflow.defn
class HumanInTheLoopAgent:
    def __init__(self) -> None:
        self._pending: str | None = None
        self._decision: str | None = None
        self._resumed = False

    @workflow.run
    async def run(self, city: str) -> str:
        def book_trip(city: str) -> str:
            """Book a trip to a city (requires human approval)."""
            return f"Booked a trip to {city}."

        trip_tool = tool_as_activity(
            book_trip, start_to_close_timeout=timedelta(seconds=30)
        )
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-5",
            tools=[trip_tool],
            interrupt_on={"book_trip": True},
            checkpointer=InMemorySaver(),
        )
        config = RunnableConfig(configurable={"thread_id": workflow.info().workflow_id})

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": f"Book a trip to {city}."}]},
            config=config,
        )
        # LangGraph returns (not raises) the pending approval under __interrupt__.
        pending = result.get("__interrupt__")
        if pending:
            self._pending = str(getattr(pending[0], "value", pending[0]))
            # Block until a client approves/rejects via the `resume` update.
            await workflow.wait_condition(lambda: self._resumed)
            # No longer paused: the query goes back to reporting None.
            self._pending = None
            result = await agent.ainvoke(
                Command(resume={"decisions": [{"type": self._decision}]}),
                config=config,
            )
        return result["messages"][-1].content

    @workflow.query
    def pending_approval(self) -> str | None:
        """Return the pending approval prompt, or ``None`` if not paused."""
        return self._pending

    @workflow.update
    async def resume(self, decision: str) -> None:
        """Resume the paused agent with ``"approve"`` or ``"reject"``."""
        self._decision = decision
        self._resumed = True

    @resume.validator
    def validate_resume(self, decision: str) -> None:
        # Runs before the update is accepted, keeping invalid decisions out of
        # workflow history entirely. Only the decisions this workflow feeds to
        # `Command(resume=...)` are allowed.
        if decision not in ("approve", "reject"):
            raise ValueError('decision must be "approve" or "reject"')


# @@@SNIPEND
