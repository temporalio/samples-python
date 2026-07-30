"""Continue-as-new with caching using the LangGraph Functional API with Temporal.

Demonstrates Temporal's continue-as-new with the LangGraph plugin's task
result cache to avoid re-executing completed @task functions across
workflow boundaries.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from langgraph.func import entrypoint, task
from temporalio import workflow
from temporalio.contrib.langgraph import cache
from temporalio.contrib.langgraph import entrypoint as temporal_entrypoint


@task
def double(data: int) -> int:
    """Stage 1: double the input."""
    return data * 2


@task
def add_50(data: int) -> int:
    """Stage 2: add 50."""
    return data + 50


@task
def triple(data: int) -> int:
    """Stage 3: triple the result."""
    return data * 3


@entrypoint()
async def pipeline_entrypoint(data: int) -> dict:
    """Run the 3-stage pipeline: double -> add_50 -> triple."""
    doubled = await double(data)
    plus_50 = await add_50(doubled)
    tripled = await triple(plus_50)
    return {"result": tripled}


all_tasks = [double, add_50, triple]

activity_options = {
    "double": {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    },
    "add_50": {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    },
    "triple": {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    },
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
        app = temporal_entrypoint("pipeline", cache=input_data.cache)
        result = await app.ainvoke(input_data.data)

        if input_data.phase < 3:
            workflow.continue_as_new(
                PipelineInput(
                    data=input_data.data,
                    cache=cache(),
                    phase=input_data.phase + 1,
                )
            )

        return result
