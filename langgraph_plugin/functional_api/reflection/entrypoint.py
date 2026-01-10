"""Reflection Agent Entrypoint Definition.

The @entrypoint function implements an iterative improvement workflow:
1. Generate initial content
2. Reflect and critique
3. Revise based on feedback
4. Check quality and loop or finish
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.reflection.tasks import (
    critique_content,
    generate_content,
    revise_content,
)


@entrypoint()
async def reflection_entrypoint(
    task_description: str, max_iterations: int = 3
) -> dict[str, Any]:
    """Run a reflection agent to generate and refine content.

    The agent will:
    1. Generate initial content
    2. Critique the content
    3. Revise if not satisfactory
    4. Repeat until quality threshold or max iterations

    Each @task call runs as a Temporal activity with automatic retries
    and durability guarantees.

    Args:
        task_description: The writing/generation task.
        max_iterations: Maximum number of reflection iterations.

    Returns:
        Dict containing the final content and iteration history.
    """
    # Step 1: Generate initial content
    current_draft = await generate_content(task_description)

    critiques: list[dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        # Step 2: Critique the current draft
        critique = await critique_content(task_description, current_draft, iteration)
        critiques.append(critique)

        # Check if satisfactory
        if critique.get("is_satisfactory", False):
            return {
                "final_content": current_draft,
                "iterations": iteration,
                "final_score": critique.get("quality_score", 0),
                "critiques": critiques,
                "status": "satisfactory",
            }

        # Check if max iterations reached
        if iteration >= max_iterations:
            return {
                "final_content": current_draft,
                "iterations": iteration,
                "final_score": critique.get("quality_score", 0),
                "critiques": critiques,
                "status": "max_iterations_reached",
            }

        # Step 3: Revise based on feedback
        current_draft = await revise_content(task_description, current_draft, critique)

    # Should not reach here, but handle edge case
    return {
        "final_content": current_draft,
        "iterations": max_iterations,
        "final_score": 0,
        "critiques": critiques,
        "status": "completed",
    }
