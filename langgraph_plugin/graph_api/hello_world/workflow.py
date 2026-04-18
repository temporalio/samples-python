"""Hello world using the LangGraph Graph API with Temporal.

The simplest possible sample: a single-node graph that processes a query string.
"""

from datetime import timedelta

from langgraph.graph import START, StateGraph
from temporalio import workflow


async def process_query(query: str) -> str:
    """Process a query and return a response."""
    return f"Processed: {query}"


hello_graph = StateGraph(str)
hello_graph.add_node(
    "process_query",
    process_query,
    metadata={"start_to_close_timeout": timedelta(seconds=10)},
)
hello_graph.add_edge(START, "process_query")


@workflow.defn
class HelloWorldWorkflow:
    @workflow.run
    async def run(self, query: str) -> str:
        return await hello_graph.compile().ainvoke(query)
