"""Supervisor Multi-Agent Entrypoint Definition.

The @entrypoint function coordinates multiple specialized agents:
- Supervisor: Decides which agent to route to
- Researcher: Gathers information
- Writer: Creates content
- Analyst: Performs calculations and analysis
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.supervisor.tasks import (
    analyst_work,
    researcher_work,
    supervisor_decide,
    writer_work,
)


@entrypoint()
async def supervisor_entrypoint(query: str, max_iterations: int = 10) -> dict[str, Any]:
    """Run a supervisor multi-agent system.

    The supervisor coordinates specialized agents to complete complex tasks.
    Each agent's work runs as a separate Temporal activity.

    Args:
        query: The user's request.
        max_iterations: Maximum agent handoffs.

    Returns:
        Dict with conversation history and final result.
    """
    available_agents = ["researcher", "writer", "analyst"]

    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]
    agent_outputs: list[str] = []

    for iteration in range(max_iterations):
        # Supervisor decides next step
        decision = await supervisor_decide(messages, available_agents)

        next_agent = decision["next_agent"]
        task_for_agent = decision["task_for_agent"]

        # Add supervisor's decision to messages
        messages.append(
            {
                "role": "supervisor",
                "content": f"Routing to {next_agent}: {task_for_agent}",
            }
        )

        if next_agent == "FINISH":
            break

        # Route to appropriate agent
        context = "\n".join(agent_outputs[-3:])  # Last 3 outputs for context

        if next_agent == "researcher":
            output = await researcher_work(task_for_agent)
        elif next_agent == "writer":
            output = await writer_work(task_for_agent, context)
        elif next_agent == "analyst":
            output = await analyst_work(task_for_agent, context)
        else:
            output = f"Unknown agent: {next_agent}"

        agent_outputs.append(output)
        messages.append({"role": next_agent, "content": output})

    # Get final summary from writer
    if agent_outputs:
        final_summary = await writer_work(
            "Summarize the work done and provide a final answer to the user's original query.",
            "\n".join(agent_outputs),
        )
    else:
        final_summary = "No agent work was performed."

    return {
        "messages": messages,
        "agent_outputs": agent_outputs,
        "final_answer": final_summary,
        "iterations": iteration + 1 if "iteration" in dir() else 0,
    }
