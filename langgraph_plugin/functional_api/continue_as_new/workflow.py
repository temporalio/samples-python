"""Continue-as-new with caching using the LangGraph Functional API with Temporal.

Same pattern as the Graph API version, but using @task and @entrypoint decorators.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from langgraph.func import entrypoint as lg_entrypoint
from langgraph.func import task
from temporalio import workflow
from temporalio.contrib.langgraph import entrypoint, get_cache


@task
def extract(data: int) -> int:
    """Stage 1: Extract -- simulate data extraction by doubling the input."""
    return data * 2


@task
def transform(data: int) -> int:
    """Stage 2: Transform -- simulate transformation by adding 50."""
    return data + 50


@task
def load(data: int) -> int:
    """Stage 3: Load -- simulate loading by tripling the result."""
    return data * 3


@lg_entrypoint()
async def pipeline_entrypoint(data: int) -> dict:
    """Run the 3-stage pipeline: extract -> transform -> load."""
    extracted = await extract(data)
    transformed = await transform(extracted)
    loaded = await load(transformed)
    return {"result": loaded}


all_tasks = [extract, transform, load]

activity_options = {
    t.func.__name__: {"start_to_close_timeout": timedelta(seconds=30)}
    for t in all_tasks
}


@dataclass
class PipelineInput:
    data: int
    cache: dict[str, Any] | None = None
    phase: int = 1


@workflow.defn
class PipelineFunctionalWorkflow:
    """Runs the pipeline, continuing-as-new after each phase.

    Input 10: 10*2=20 -> 20+50=70 -> 70*3=210
    Each task executes once; phases 2 and 3 use cached results.
    """

    @workflow.run
    async def run(self, input_data: PipelineInput) -> dict[str, Any]:
        result = await entrypoint("pipeline", cache=input_data.cache).ainvoke(
            input_data.data
        )

        if input_data.phase < 3:
            workflow.continue_as_new(
                PipelineInput(
                    data=input_data.data,
                    cache=get_cache(),
                    phase=input_data.phase + 1,
                )
            )

        return result
