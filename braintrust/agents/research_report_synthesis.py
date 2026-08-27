from typing import List
from temporalio import workflow
from datetime import timedelta
from .shared import ResearchReport, ResearchPlan, SearchResult, today_str
from .config import COMPLEX_REASONING_MODEL
from activities.invoke_model import invoke_model, InvokeModelRequest

REPORT_SYNTHESIS_INSTRUCTIONS = f"""
You are a research synthesis expert who creates comprehensive research reports.

CORE RESPONSIBILITIES:
1. Synthesize all research into a coherent narrative
2. Structure information logically with evidence support
3. Provide comprehensive citations
4. Assess confidence levels and acknowledge limitations
5. Generate follow-up questions for deeper research

REPORT STRUCTURE:
1. **Executive Summary**: Core findings and conclusions (1-2 paragraphs)
2. **Detailed Analysis**: Examination organized by themes with evidence
3. **Key Findings**: Bullet-point list of important discoveries
4. **Confidence Assessment**: Rate findings as High/Medium/Low/Uncertain
5. **Citations**: Complete source list with URLs
6. **Follow-up Questions**: Up to 5 areas for additional research, as warranted

APPROACH:
- Address contradictory findings transparently
- Weight authoritative sources more heavily
- Distinguish facts from expert opinions
- Be explicit about information limitations

OUTPUT REQUIREMENTS:
- executive_summary: 1-2 paragraph summary of core findings
- detailed_analysis: Multi-paragraph analysis organized by themes
- key_findings: Bullet-point discoveries
- confidence_assessment: Assessment of finding reliability
- citations: All sources referenced
- follow_up_questions: 3-5 specific questions for further research

TODAY'S DATE: {today_str()}
"""


async def generate_synthesis(
    original_query: str, research_plan: ResearchPlan, search_results: List[SearchResult]
) -> ResearchReport:
    # Prepare comprehensive input with all research context
    synthesis_input = f"""
ORIGINAL RESEARCH QUERY: {original_query}

RESEARCH PLAN:
Research Question: {research_plan.research_question}
Key Aspects Investigated: {
        ", ".join([aspect.aspect for aspect in research_plan.key_aspects])
    }
Search Strategy Used: {research_plan.search_strategy}
Success Criteria: {", ".join(research_plan.success_criteria)}

SEARCH RESULTS TO SYNTHESIZE:
{
        chr(10).join(
            [
                f"Query: {result.query}{chr(10)}Findings: {result.key_findings}{chr(10)}Relevance: {result.relevance_score}{chr(10)}Sources: {', '.join(result.sources)}{chr(10)}Citations: {', '.join(result.citations)}{chr(10)}"
                for result in search_results
            ]
        )
    }

Please synthesize all this information into a comprehensive research report following the specified structure and quality standards.
"""
    result = await workflow.execute_activity(
        invoke_model,
        InvokeModelRequest(
            model=COMPLEX_REASONING_MODEL,
            instructions=REPORT_SYNTHESIS_INSTRUCTIONS,  # Fallback
            input=synthesis_input,
            prompt_slug="report-synthesis",  # Load from Braintrust if available
            response_format=ResearchReport,
        ),
        start_to_close_timeout=timedelta(seconds=300),
        summary="Generating research report synthesis",
    )

    return result.response
