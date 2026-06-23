from .shared import ResearchPlan, today_str
from .config import COMPLEX_REASONING_MODEL
from activities.invoke_model import invoke_model, InvokeModelRequest
from temporalio import workflow
from datetime import timedelta

RESEARCH_PLANNING_INSTRUCTIONS = f"""
You are a research planning specialist who creates focused research strategies.

CORE RESPONSIBILITIES:
1. Decompose the user's question into 3-7 key research aspects
2. Identify required sources and evidence types
3. Design a practical search strategy
4. Set clear success criteria

OUTPUT REQUIREMENTS:
- research_question: Clarified version of the original query
- key_aspects: Specific areas requiring investigation, each with:
  - aspect: The research area name
  - priority: 1-5 ranking (5 highest priority)  
  - description: What needs to be investigated
- expected_sources: Types of sources likely to contain relevant information
- search_strategy: High-level approach for information gathering
- success_criteria: Specific indicators of research completeness

TODAY'S DATE: {today_str()}
"""


async def plan_research(query: str) -> ResearchPlan:
    result = await workflow.execute_activity(
        invoke_model,
        InvokeModelRequest(
            model=COMPLEX_REASONING_MODEL,
            instructions=RESEARCH_PLANNING_INSTRUCTIONS,
            input=f"Research query: {query}",
            response_format=ResearchPlan,
        ),
        start_to_close_timeout=timedelta(seconds=300),
        summary="Planning research",
    )
    return result.response
