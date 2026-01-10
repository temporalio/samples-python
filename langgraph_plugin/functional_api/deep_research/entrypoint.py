"""Deep Research Agent Entrypoint Definition.

The @entrypoint function orchestrates multi-step research:
1. Plan research queries
2. Execute searches in parallel
3. Evaluate and iterate if needed
4. Synthesize findings into a report
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.deep_research.tasks import (
    execute_search,
    plan_research,
    synthesize_report,
)


@entrypoint()
async def deep_research_entrypoint(
    topic: str, max_iterations: int = 2
) -> dict[str, Any]:
    """Perform deep research on a topic.

    Demonstrates:
    - Planning research queries
    - Parallel task execution for multiple searches
    - Iterative research refinement
    - Report synthesis

    Args:
        topic: The research topic.
        max_iterations: Maximum research iterations.

    Returns:
        Dict with research report and metadata.
    """
    all_results: list[dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        # Step 1: Plan research queries
        queries = await plan_research(topic)

        # Step 2: Execute searches in parallel
        # Start all search tasks concurrently
        search_futures = [execute_search(q["query"], q["purpose"]) for q in queries]

        # Wait for all searches to complete
        search_results = [await future for future in search_futures]
        all_results.extend(search_results)

        # Step 3: Evaluate results
        relevant_count = sum(1 for r in search_results if r.get("relevant", False))

        # Check if we have enough relevant results
        if relevant_count >= 2 or iteration >= max_iterations:
            break

    # Step 4: Synthesize report
    report = await synthesize_report(topic, all_results)

    return {
        "topic": topic,
        "report": report,
        "iterations": iteration,
        "total_searches": len(all_results),
        "relevant_results": sum(1 for r in all_results if r.get("relevant", False)),
    }
