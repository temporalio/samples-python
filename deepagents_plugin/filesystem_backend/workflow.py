"""Durable real filesystem I/O via ``TemporalBackend``.

A Deep Agent's built-in file tools (``write_file``, ``read_file``, ``ls``, …)
delegate to a *backend*. The default ``StateBackend`` keeps files in agent state
— pure workflow state, replay-safe, no wrapping needed. A ``FilesystemBackend``,
by contrast, touches real disk, which must not happen from workflow code.

``TemporalBackend(inner, activity_options=...)`` wraps such a backend so each
file operation the agent's tools invoke becomes a ``deepagents.backend_op``
activity instead of running in the workflow. The agent code is unchanged; only
the backend is wrapped.

``root_dir`` is passed in as a workflow argument (rather than read from the
environment inside the workflow) to keep the workflow deterministic.
"""

# @@@SNIPSTART python-deepagents-filesystem-backend-workflow
from datetime import timedelta

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from temporalio import workflow
from temporalio.contrib.deepagents import TemporalBackend


@workflow.defn
class FilesystemAgent:
    @workflow.run
    async def run(self, root_dir: str, instruction: str) -> str:
        # Wrap the real-I/O backend so every file op runs in an activity.
        backend = TemporalBackend(
            # virtual_mode roots every path the agent uses under root_dir, so the
            # agent's file tools stay sandboxed to this working directory.
            FilesystemBackend(root_dir=root_dir, virtual_mode=True),
            activity_options={"start_to_close_timeout": timedelta(seconds=30)},
        )
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-5",
            # TemporalBackend delegates the backend protocol to the wrapped
            # backend at runtime, which the static type can't see through.
            backend=backend,  # type: ignore[arg-type]
            system_prompt=(
                "You are a file-savvy assistant. Use the write_file and "
                "read_file tools to complete the task."
            ),
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": instruction}]}
        )
        return result["messages"][-1].content


# @@@SNIPEND
