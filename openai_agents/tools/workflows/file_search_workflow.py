from __future__ import annotations

from agents import Agent, FileSearchTool, Runner
from temporalio import workflow


@workflow.defn
class FileSearchWorkflow:
    @workflow.run
    async def run(self, question: str, vector_store_id: str) -> str:
        agent = Agent(
            name="File searcher",
            instructions="You are a helpful agent.",
            tools=[
                FileSearchTool(
                    max_num_results=3,
                    vector_store_ids=[vector_store_id],
                    include_search_results=True,
                )
            ],
        )

        result = await Runner.run(agent, question)
        return result.final_output
