"""Control flow sample using the LangGraph Functional API with Temporal.

Demonstrates the Functional API's advantage for complex control flow:
  - Parallel task execution (launch multiple tasks concurrently)
  - Sequential for-loop processing
  - Conditional if/else branching based on intermediate results
"""

from datetime import timedelta

from langgraph.func import entrypoint as lg_entrypoint
from langgraph.func import task
from temporalio import workflow
from temporalio.contrib.langgraph import entrypoint


@task
def validate_item(item: str) -> bool:
    """Validate an item. Returns True if the item is non-empty and well-formed."""
    return len(item.strip()) > 0 and not item.startswith("INVALID:")


@task
def classify_item(item: str) -> str:
    """Classify an item as 'urgent' or 'normal' based on its content."""
    return "urgent" if "urgent" in item.lower() else "normal"


@task
def process_urgent(item: str) -> str:
    """Process an urgent item with priority handling."""
    return f"[PRIORITY] Processed: {item}"


@task
def process_normal(item: str) -> str:
    """Process a normal item with standard handling."""
    return f"[STANDARD] Processed: {item}"


@task
def summarize(results: list[str]) -> str:
    """Produce a summary of all processed results."""
    urgent_count = sum(1 for r in results if r.startswith("[PRIORITY]"))
    normal_count = sum(1 for r in results if r.startswith("[STANDARD]"))
    return (
        f"Processed {len(results)} items "
        f"({urgent_count} urgent, {normal_count} normal)"
    )


@lg_entrypoint()
async def control_flow_pipeline(items: list[str]) -> dict:
    """Process a batch of items with parallel validation, sequential
    classification, and conditional routing.
    """
    # PARALLEL: Validate all items concurrently.
    # Creating task futures without awaiting launches them in parallel.
    validation_futures = [validate_item(item) for item in items]
    valid_flags = [await f for f in validation_futures]
    valid_items = [
        item for item, is_valid in zip(items, valid_flags) if is_valid
    ]

    # SEQUENTIAL + CONDITIONAL: Process each valid item
    results = []
    for item in valid_items:
        category = await classify_item(item)
        if category == "urgent":
            result = await process_urgent(item)
        else:
            result = await process_normal(item)
        results.append(result)

    # Aggregate all results
    summary_text = await summarize(results)

    return {"results": results, "summary": summary_text, "total": len(results)}


all_tasks = [
    validate_item,
    classify_item,
    process_urgent,
    process_normal,
    summarize,
]

activity_options = {
    t.func.__name__: {"start_to_close_timeout": timedelta(seconds=30)}
    for t in all_tasks
}


@workflow.defn
class ControlFlowWorkflow:
    @workflow.run
    async def run(self, items: list[str]) -> dict:
        return await entrypoint("control_flow").ainvoke(items)
