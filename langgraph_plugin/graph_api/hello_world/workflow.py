"""Hello world using the LangGraph Graph API with Temporal.

The simplest possible sample: a single-node graph that processes a query string.
"""

from datetime import timedelta

from langgraph.graph import START, StateGraph
from temporalio import workflow
from temporalio.contrib.langgraph import graph


async def process_query(query: str) -> str:
    """Process a query and return a response."""
    return f"Processed: {query}"


def build_graph() -> StateGraph:
    """Construct a single-node graph."""
    g = StateGraph(str)
    g.add_node(
        "process_query",
        process_query,
        metadata={"start_to_close_timeout": timedelta(seconds=10)},
    )
    g.add_edge(START, "process_query")
    return g


@workflow.defn
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, query: str) -> str:
        return await graph("hello-world").compile().ainvoke(query)
