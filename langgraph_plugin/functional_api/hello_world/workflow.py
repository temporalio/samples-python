"""Hello world using the LangGraph Functional API with Temporal.

The simplest possible sample: a single task called from an entrypoint.
"""

from datetime import timedelta

from langgraph.func import entrypoint, task
from temporalio import workflow
from temporalio.contrib.langgraph import entrypoint as temporal_entrypoint


@task
def process_query(query: str) -> str:
    """Process a query and return a response."""
    return f"Processed: {query}"


@entrypoint()
async def hello_entrypoint(query: str) -> dict:
    """Process the query and return it in a result dict."""
    result = await process_query(query)
    return {"result": result}


all_tasks = [process_query]

activity_options = {
    "process_query": {
        "execute_in": "activity",
        "start_to_close_timeout": timedelta(seconds=10),
    },
}


@workflow.defn
class HelloWorldFunctionalWorkflow:
    @workflow.run
    async def run(self, query: str) -> dict:
        return await temporal_entrypoint("hello-world").ainvoke(query)
