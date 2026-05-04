"""Hello world using the LangGraph Graph API with Temporal.

The simplest possible sample: a single-node graph that processes a query string.
"""

from datetime import timedelta

from langgraph.graph import START, StateGraph
from temporalio import workflow
from temporalio.contrib.langgraph import graph as temporal_graph
from typing_extensions import TypedDict


class State(TypedDict):
    value: str


async def process_query(state: State) -> dict[str, str]:
    """Process a query and return a response."""
    return {"value": f"Processed: {state['value']}"}


def make_hello_graph() -> StateGraph:
    g = StateGraph(State)
    g.add_node(
        "process_query",
        process_query,
        metadata={
            "execute_in": "activity",
            "start_to_close_timeout": timedelta(seconds=10),
        },
    )
    g.add_edge(START, "process_query")
    return g


@workflow.defn
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, query: str) -> str:
        result = await temporal_graph("hello-world").compile().ainvoke({"value": query})
        return result["value"]
