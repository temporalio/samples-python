from .shared import QueryPlan, ResearchPlan, today_str
from .config import EFFICIENT_PROCESSING_MODEL
from activities.invoke_model import invoke_model, InvokeModelRequest
from temporalio import workflow
from datetime import timedelta

QUERY_GENERATION_INSTRUCTIONS = f"""
You are a search query specialist who crafts effective web searches.

CORE RESPONSIBILITIES:
1. Generate 3-5 diverse search queries based on the research plan
2. Balance specificity with discoverability
3. Target different information types (factual, analytical, recent, historical)

APPROACH:
- Vary query styles: direct questions, topic + keywords, source-specific searches
- Include temporal modifiers when relevant (recent, 2024, historical)
- Use domain-specific terminology appropriately

OUTPUT REQUIREMENTS:
- queries: Search queries, each with:
  - query: The actual search string
  - rationale: Why this query addresses research needs  
  - expected_info_type: One of "factual_data", "expert_analysis", "case_studies", "recent_news"
  - priority: 1-5 (5 highest priority)

TODAY'S DATE: {today_str()}
"""


async def generate_queries(research_plan: ResearchPlan) -> QueryPlan:
    # Prepare input with research plan context
    plan_context = f"""
Research Question: {research_plan.research_question}

Key Aspects to Research:
{chr(10).join([f"- {aspect.aspect} (Priority: {aspect.priority}): {aspect.description}" for aspect in research_plan.key_aspects])}

Expected Sources: {", ".join(research_plan.expected_sources)}
Search Strategy: {research_plan.search_strategy}
Success Criteria: {", ".join(research_plan.success_criteria)}
"""

    result = await workflow.execute_activity(
        invoke_model,
        InvokeModelRequest(
            model=EFFICIENT_PROCESSING_MODEL,
            instructions=QUERY_GENERATION_INSTRUCTIONS,
            input=plan_context,
            response_format=QueryPlan,
        ),
        start_to_close_timeout=timedelta(seconds=300),
        summary="Generating search queries",
    )

    return result.response
