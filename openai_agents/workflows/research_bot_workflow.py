from temporalio import workflow

from openai_agents.workflows.research_agents.research_manager import ResearchManager


@workflow.defn
class ResearchWorkflow:
    @workflow.run
    async def run(self, query: str) -> str:
        return await ResearchManager().run(query)
