"""Task definitions for the Deep Research Agent.

Each @task runs as a Temporal activity with automatic retries.
Demonstrates parallel task execution for multiple web searches.
"""

import os
from typing import Any

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.func import task
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """A search query to execute."""

    query: str = Field(description="The search query to execute")
    purpose: str = Field(description="What information this query aims to find")


class ResearchPlan(BaseModel):
    """Research plan with multiple search queries."""

    queries: list[SearchQuery] = Field(
        description="List of search queries to execute", min_length=1, max_length=5
    )


# Initialize DuckDuckGo search tool
search_tool = DuckDuckGoSearchRun()


@task
async def plan_research(topic: str) -> list[dict[str, str]]:
    """Plan the research by generating search queries.

    Args:
        topic: The research topic.

    Returns:
        List of search queries with purposes.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    plan_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a research planner. Given a research topic, generate 2-4 search
queries that will help gather comprehensive information. Each query should
target a different aspect of the topic.

Consider:
- Core concepts and definitions
- Key features and capabilities
- Use cases and applications
- Comparisons or alternatives""",
            ),
            ("human", "Research topic: {topic}"),
        ]
    )

    planner = plan_prompt | model.with_structured_output(ResearchPlan)
    plan: Any = await planner.ainvoke({"topic": topic})

    return [{"query": q.query, "purpose": q.purpose} for q in plan.queries]


@task
async def execute_search(query: str, purpose: str) -> dict[str, Any]:
    """Execute a single web search query using DuckDuckGo.

    Each search runs as a separate Temporal activity for durability.

    Args:
        query: The search query.
        purpose: What information this query aims to find.

    Returns:
        Dict with query, purpose, results, and relevance flag.
    """
    try:
        results = search_tool.invoke(query)
        has_results = bool(results and len(results.strip()) > 0)
    except Exception as e:
        results = f"Search failed: {e}"
        has_results = False

    return {
        "query": query,
        "purpose": purpose,
        "results": results,
        "relevant": has_results,
    }


@task
async def synthesize_report(topic: str, search_results: list[dict[str, Any]]) -> str:
    """Synthesize research findings into a comprehensive report.

    Args:
        topic: The research topic.
        search_results: Results from all searches.

    Returns:
        The synthesized research report.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3,
    )

    # Compile all findings
    findings = []
    for result in search_results:
        if result.get("relevant", False):
            findings.append(f"### {result['purpose']}\n{result['results']}")

    if not findings:
        findings_text = "Limited information was found on this topic."
    else:
        findings_text = "\n\n".join(findings)

    synthesis_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a research synthesizer. Create a comprehensive research report
from the gathered findings. Structure the report with:
1. Executive Summary - Key takeaways in 2-3 sentences
2. Main Findings - Detailed information organized by topic
3. Conclusions - Synthesis of the research

Be thorough but concise. Cite the source topics when presenting findings.""",
            ),
            (
                "human",
                "Research Topic: {topic}\n\nGathered Findings:\n{findings}",
            ),
        ]
    )

    chain = synthesis_prompt | model | StrOutputParser()
    report = await chain.ainvoke({"topic": topic, "findings": findings_text})

    return report
