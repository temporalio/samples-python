"""Continue-as-new with caching using the LangGraph Graph API with Temporal.

Demonstrates how to use Temporal's continue-as-new with LangGraph's task result
caching to avoid re-executing already-completed graph nodes across workflow
boundaries.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from langgraph.graph import START, StateGraph
from temporalio import workflow
from temporalio.contrib.langgraph import cache, graph
from typing_extensions import TypedDict


class State(TypedDict):
    value: int


async def extract(state: State) -> dict[str, int]:
    """Stage 1: Extract -- simulate data extraction by doubling the input."""
    return {"value": state["value"] * 2}


async def transform(state: State) -> dict[str, int]:
    """Stage 2: Transform -- simulate transformation by adding 50."""
    return {"value": state["value"] + 50}


async def load(state: State) -> dict[str, int]:
    """Stage 3: Load -- simulate loading by tripling the result."""
    return {"value": state["value"] * 3}


def make_pipeline_graph() -> StateGraph:
    node_metadata = {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=30),
    }
    g = StateGraph(State)
    g.add_node("extract", extract, metadata=node_metadata)
    g.add_node("transform", transform, metadata=node_metadata)
    g.add_node("load", load, metadata=node_metadata)
    g.add_edge(START, "extract")
    g.add_edge("extract", "transform")
    g.add_edge("transform", "load")
    return g


@dataclass
class PipelineInput:
    data: int
    cache: dict[str, Any] | None = None
    phase: int = 1  # continues-as-new after phases 1 and 2


@workflow.defn
class PipelineWorkflow:
    """Runs a 3-stage pipeline, continuing-as-new after each phase.

    Phase 1: all 3 stages execute, continues-as-new with cache.
    Phase 2: all 3 stages cached (instant), continues-as-new.
    Phase 3: all 3 stages cached (instant), returns final result.

    Input 10: 10*2=20 -> 20+50=70 -> 70*3=210
    """

    @workflow.run
    async def run(self, input_data: PipelineInput) -> int:
        app = graph("pipeline", cache=input_data.cache).compile()
        result = await app.ainvoke({"value": input_data.data})

        if input_data.phase < 3:
            workflow.continue_as_new(
                PipelineInput(
                    data=input_data.data,
                    cache=cache(),
                    phase=input_data.phase + 1,
                )
            )

        return result["value"]
