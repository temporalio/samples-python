"""Continue-as-New Entrypoint Definition.

Demonstrates partial execution with task caching for continue-as-new.
"""

from typing import Any

from langgraph.func import entrypoint

from langgraph_plugin.functional_api.continue_as_new.tasks import (
    step_1,
    step_2,
    step_3,
    step_4,
    step_5,
)


@entrypoint()
async def pipeline_entrypoint(input_data: dict[str, Any]) -> dict[str, Any]:
    """Pipeline entrypoint with 5 sequential tasks.

    Supports partial execution via 'stop_after' parameter.
    This enables the workflow to:
    1. Run tasks 1-3, cache results, continue-as-new
    2. Run all 5 tasks, but 1-3 use cached results

    Args:
        input_data: Dict with:
            - value: Starting integer value
            - stop_after: Stop after N tasks (1-5), default 5

    Returns:
        Dict with result and number of completed tasks.

    Calculation for value=10, all 5 tasks:
        10 * 2 = 20 -> 20 + 5 = 25 -> 25 * 3 = 75 -> 75 - 10 = 65 -> 65 + 100 = 165
    """
    value = input_data["value"]
    stop_after = input_data.get("stop_after", 5)

    result = value

    # Task 1
    result = await step_1(result)
    if stop_after == 1:
        return {"result": result, "completed_tasks": 1}

    # Task 2
    result = await step_2(result)
    if stop_after == 2:
        return {"result": result, "completed_tasks": 2}

    # Task 3
    result = await step_3(result)
    if stop_after == 3:
        return {"result": result, "completed_tasks": 3}

    # Task 4
    result = await step_4(result)
    if stop_after == 4:
        return {"result": result, "completed_tasks": 4}

    # Task 5
    result = await step_5(result)
    return {"result": result, "completed_tasks": 5}
