"""Hello world using the LangGraph Functional API with Temporal.

The simplest possible sample: a single task called from an entrypoint.
"""

from datetime import timedelta

from langgraph.func import entrypoint as lg_entrypoint
from langgraph.func import task
from temporalio import workflow
from temporalio.contrib.langgraph import entrypoint


@task
def process_query(query: str) -> str:
    """Process a query and return a response."""
    return f"Processed: {query}"


@lg_entrypoint()
async def hello_entrypoint(query: str) -> dict:
    """Process the query and return it in a result dict."""
    result = await process_query(query)
    return {"result": result}


all_tasks = [process_query]

activity_options = {
    t.func.__name__: {"start_to_close_timeout": timedelta(seconds=10)}
    for t in all_tasks
}


@workflow.defn
class HelloWorldFunctionalWorkflow:
    @workflow.run
    async def run(self, query: str) -> dict:
        return await entrypoint("hello-world").ainvoke(query)
