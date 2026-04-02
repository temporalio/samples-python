"""ReAct Agent Entrypoint Definition.

The @entrypoint function implements the ReAct (Reasoning and Acting) pattern:
1. Think: LLM decides what action to take (call_model task)
2. Act: Execute the chosen tool (execute_tools task)
3. Observe: Feed tool results back to LLM
4. Repeat until done
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.react_agent.tasks import call_model, execute_tools


@entrypoint()
async def react_agent_entrypoint(
    query: str, max_iterations: int = 10
) -> dict[str, Any]:
    """Run a ReAct agent to answer a query.

    The agent will:
    1. Think about what information is needed
    2. Use tools to gather information
    3. Synthesize a final answer

    Each @task call (call_model, execute_tools) runs as a Temporal activity
    with automatic retries and durability guarantees.

    Args:
        query: The user's question or request.
        max_iterations: Maximum number of think/act iterations.

    Returns:
        Dict containing the conversation messages and final answer.
    """
    # Initialize conversation with user query
    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]

    for iteration in range(max_iterations):
        # Think: Call LLM to decide action
        response = await call_model(messages)
        messages.append(response)

        # Check if model wants to use tools
        tool_calls = response.get("tool_calls")

        if not tool_calls:
            # Model is done - return final answer
            return {
                "messages": messages,
                "final_answer": response.get("content", ""),
                "iterations": iteration + 1,
            }

        # Act: Execute the requested tools
        tool_results = await execute_tools(tool_calls)

        # Observe: Add tool results to conversation
        messages.extend(tool_results)

    # Max iterations reached
    return {
        "messages": messages,
        "final_answer": "Max iterations reached without final answer",
        "iterations": max_iterations,
    }
