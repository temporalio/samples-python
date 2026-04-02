"""Plan-and-Execute Agent Entrypoint Definition.

The @entrypoint function implements a plan-and-execute pattern:
1. Create a plan with specific steps
2. Execute each step using available tools
3. Generate a final response from the results
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.plan_and_execute.tasks import (
    create_plan,
    execute_step,
    generate_response,
)


@entrypoint()
async def plan_execute_entrypoint(objective: str) -> dict[str, Any]:
    """Run a plan-and-execute agent.

    The agent will:
    1. Create a plan with specific steps
    2. Execute each step sequentially
    3. Generate a final response

    Each @task call runs as a Temporal activity with automatic retries.

    Args:
        objective: The task to accomplish.

    Returns:
        Dict with plan, step results, and final response.
    """
    # Step 1: Create the plan
    plan = await create_plan(objective)

    # Step 2: Execute each step
    step_results: list[dict[str, Any]] = []

    for step in plan["steps"]:
        result = await execute_step(
            step_number=step["step_number"],
            description=step["description"],
            tool_hint=step["tool_hint"],
        )
        step_results.append(result)

    # Step 3: Generate final response
    final_response = await generate_response(objective, step_results)

    return {
        "objective": objective,
        "plan": plan,
        "step_results": step_results,
        "final_response": final_response,
    }
