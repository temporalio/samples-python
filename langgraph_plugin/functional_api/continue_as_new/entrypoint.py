"""Continue-as-New Entrypoint Definition.

Demonstrates a pipeline that can be interrupted via should_continue callback.
The entrypoint itself has NO knowledge of continue-as-new - it just runs
all tasks. The workflow controls when to checkpoint via the callback.
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

    This entrypoint runs all 5 tasks. If should_continue callback is provided
    to ainvoke() and returns False after a task completes, execution will
    stop early and return a checkpoint for continue-as-new.

    Args:
        input_data: Dict with:
            - value: Starting integer value

    Returns:
        Dict with result and number of completed tasks.

    Calculation for value=10, all 5 tasks:
        10 * 2 = 20 -> 20 + 5 = 25 -> 25 * 3 = 75 -> 75 - 10 = 65 -> 65 + 100 = 165
    """
    value = input_data["value"]

    result = value

    # Task 1: multiply by 2
    result = await step_1(result)

    # Task 2: add 5
    result = await step_2(result)

    # Task 3: multiply by 3
    result = await step_3(result)

    # Task 4: subtract 10
    result = await step_4(result)

    # Task 5: add 100
    result = await step_5(result)

    return {"result": result, "completed_tasks": 5}
