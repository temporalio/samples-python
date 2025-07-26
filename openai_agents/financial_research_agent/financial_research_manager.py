from __future__ import annotations

import asyncio
from collections.abc import Sequence

from temporalio import workflow

from agents import RunConfig, Runner, RunResult, custom_span, trace

from openai_agents.financial_research_agent.agents.financials_agent import (
    new_financials_agent,
)
from openai_agents.financial_research_agent.agents.planner_agent import (
    FinancialSearchItem,
    FinancialSearchPlan,
    new_planner_agent,
)
from openai_agents.financial_research_agent.agents.risk_agent import new_risk_agent
from openai_agents.financial_research_agent.agents.search_agent import (
    new_search_agent,
)
from openai_agents.financial_research_agent.agents.verifier_agent import (
    VerificationResult,
    new_verifier_agent,
)
from openai_agents.financial_research_agent.agents.writer_agent import (
    FinancialReportData,
    new_writer_agent,
)


async def _summary_extractor(run_result: RunResult) -> str:
    """Custom output extractor for sub-agents that return an AnalysisSummary."""
    # The financial/risk analyst agents emit an AnalysisSummary with a `summary` field.
    # We want the tool call to return just that summary text so the writer can drop it inline.
    return str(run_result.final_output.summary)


class FinancialResearchManager:
    """
    Orchestrates the full flow: planning, searching, sub-analysis, writing, and verification.
    """

    def __init__(self) -> None:
        self.run_config = RunConfig()
        self.planner_agent = new_planner_agent()
        self.search_agent = new_search_agent()
        self.financials_agent = new_financials_agent()
        self.risk_agent = new_risk_agent()
        self.writer_agent = new_writer_agent()
        self.verifier_agent = new_verifier_agent()

    async def run(self, query: str) -> str:
        with trace("Financial research trace"):
            search_plan = await self._plan_searches(query)
            search_results = await self._perform_searches(search_plan)
            report = await self._write_report(query, search_results)
            verification = await self._verify_report(report)

        # Return formatted output
        result = f"""=====REPORT=====

{report.markdown_report}

=====FOLLOW UP QUESTIONS=====

{chr(10).join(report.follow_up_questions)}

=====VERIFICATION=====

Verified: {verification.verified}
Issues: {verification.issues}"""

        return result

    async def _plan_searches(self, query: str) -> FinancialSearchPlan:
        result = await Runner.run(
            self.planner_agent,
            f"Query: {query}",
            run_config=self.run_config,
        )
        return result.final_output_as(FinancialSearchPlan)

    async def _perform_searches(
        self, search_plan: FinancialSearchPlan
    ) -> Sequence[str]:
        with custom_span("Search the web"):
            tasks = [
                asyncio.create_task(self._search(item)) for item in search_plan.searches
            ]
            results: list[str] = []
            for task in workflow.as_completed(tasks):
                result = await task
                if result is not None:
                    results.append(result)
            return results

    async def _search(self, item: FinancialSearchItem) -> str | None:
        input_data = f"Search term: {item.query}\nReason: {item.reason}"
        try:
            result = await Runner.run(
                self.search_agent,
                input_data,
                run_config=self.run_config,
            )
            return str(result.final_output)
        except Exception:
            return None

    async def _write_report(
        self, query: str, search_results: Sequence[str]
    ) -> FinancialReportData:
        # Expose the specialist analysts as tools so the writer can invoke them inline
        # and still produce the final FinancialReportData output.
        fundamentals_tool = self.financials_agent.as_tool(
            tool_name="fundamentals_analysis",
            tool_description="Use to get a short write-up of key financial metrics",
            custom_output_extractor=_summary_extractor,
        )
        risk_tool = self.risk_agent.as_tool(
            tool_name="risk_analysis",
            tool_description="Use to get a short write-up of potential red flags",
            custom_output_extractor=_summary_extractor,
        )
        writer_with_tools = self.writer_agent.clone(
            tools=[fundamentals_tool, risk_tool]
        )

        input_data = (
            f"Original query: {query}\nSummarized search results: {search_results}"
        )
        result = await Runner.run(
            writer_with_tools,
            input_data,
            run_config=self.run_config,
        )
        return result.final_output_as(FinancialReportData)

    async def _verify_report(self, report: FinancialReportData) -> VerificationResult:
        result = await Runner.run(
            self.verifier_agent,
            report.markdown_report,
            run_config=self.run_config,
        )
        return result.final_output_as(VerificationResult)
