from temporalio import workflow
from temporalio.exceptions import ApplicationError
import asyncio
from typing import List

from agents.research_planning import plan_research
from agents.research_query_generation import generate_queries
from agents.research_web_search import search_web
from agents.research_report_synthesis import generate_synthesis
from agents.shared import SearchResult


@workflow.defn
class DeepResearchWorkflow:
    @workflow.run
    async def run(self, query: str) -> str:
        # Step 1: Research Planning
        research_plan = await plan_research(query)

        # Step 2: Query Generation
        query_plan = await generate_queries(research_plan)

        # Step 3: Web Search (parallel execution with resilience)
        search_results = await self._execute_searches(query_plan.queries)

        # Ensure we have at least one successful search result
        if not search_results:
            raise ApplicationError(
                "All web searches failed - cannot generate report",
                "NO_SEARCH_RESULTS",
                non_retryable=True,
            )

        # Step 4: Report Synthesis
        final_report = await generate_synthesis(query, research_plan, search_results)

        # Format the final output
        formatted_report = self._format_final_report(query, final_report)
        return formatted_report

    async def _execute_searches(self, search_queries) -> List[SearchResult]:
        """Execute web searches in parallel with resilience to individual failures"""

        # Create individual search coroutines
        async def execute_single_search(search_query):
            try:
                return await search_web(search_query)
            except Exception as e:
                workflow.logger.exception(
                    f"Search failed for query '{search_query.query}': {e}"
                )
                return None

        # Execute all searches in parallel
        search_tasks = [execute_single_search(query) for query in search_queries]
        results = await asyncio.gather(*search_tasks)

        # Filter out None results
        return [result for result in results if result is not None]

    def _format_final_report(self, original_query, report) -> str:
        """Format the final report for display"""
        return f"""
# Deep Research Report

**Research Query:** {original_query}

## Executive Summary
{report.executive_summary}

## Detailed Analysis
{report.detailed_analysis}

## Key Findings
{chr(10).join([f"• {finding}" for finding in report.key_findings])}

## Confidence Assessment
{report.confidence_assessment}

## Sources and Citations
{chr(10).join([f"• {citation}" for citation in report.citations])}

## Recommended Follow-up Questions
{chr(10).join([f"• {question}" for question in report.follow_up_questions])}

"""
