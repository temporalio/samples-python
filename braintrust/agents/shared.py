from pydantic import BaseModel
from typing import List
from datetime import datetime


class ResearchAspect(BaseModel):
    aspect: str
    priority: int
    description: str


class ResearchPlan(BaseModel):
    research_question: str
    key_aspects: List[ResearchAspect]
    expected_sources: List[str]
    search_strategy: str
    success_criteria: List[str]


class SearchQuery(BaseModel):
    query: str
    rationale: str
    expected_info_type: str
    priority: int


class QueryPlan(BaseModel):
    queries: List[SearchQuery]


class SearchResult(BaseModel):
    query: str
    sources: List[str]
    key_findings: str
    relevance_score: float
    citations: List[str]


class ResearchReport(BaseModel):
    executive_summary: str
    detailed_analysis: str
    key_findings: List[str]
    confidence_assessment: str
    citations: List[str]
    follow_up_questions: List[str]


def today_str() -> str:
    # Use Temporal workflow time when running inside a workflow.
    # Fall back to the system clock when outside a workflow context.
    try:
        from temporalio import workflow  # type: ignore

        now = workflow.now()
    except Exception:
        now = datetime.now()
    return f"{now:%a} {now:%b} {now.day}, {now:%Y}"
