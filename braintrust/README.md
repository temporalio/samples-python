<!-- 
description: Build a simple deep research system embodying the standard
deep research architecture.
tags: [agents, toolcalling, python]
priority: 399
-->

# Deep Research

Deep research systems combine multiple agents with information retrieval from
the web or other sources to produce evidence-based reports on specific topics.
Commercial implementations include
[Anthropic Research](https://www.anthropic.com/engineering/multi-agent-research-system),
[OpenAI Deep Research](https://openai.com/index/introducing-deep-research/), and
[Google Gemini Deep Research](https://gemini.google/overview/deep-research/).

This recipe demonstrates a simple deep research system embodying the standard
deep research architecture. Deep research spans the following four phases:

- **Planning**. Task decomposition and research strategy formulation. This
  involves identifying separate aspects of the research problem that can be
  worked on independently.
- **Question Development/Query Generation**. Designing queries for each of the
  research questions.
- **Web Exploration/Information Retrieval**. Searching the web to retrieve
  documents relevant to the research question. Extracting and summarizing
  relevant information.
- **Report Generation/Synthesis**. Synthesizing findings into comprehensive,
  well-cited reports.

Deep research tasks can involve dozens of searches and process hundreds of
documents. This creates many possible failure modes that durable execution helps
protect against.

This recipe uses OpenAI's Responses API, which includes a tool for web search.
It also uses OpenAI's
[Structured Outputs API](https://platform.openai.com/docs/guides/structured-outputs),
which asks the model to generate outputs corresponding to desired data
structures.

## Prerequisites

Set the required environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export BRAINTRUST_API_KEY="your-braintrust-api-key"
export BRAINTRUST_PROJECT_NAME="your-project-name"       # optional, defaults to "deep-research"
```

## Running

This example requires three terminal tabs.

**Terminal 1** - Start the Temporal Dev Server:

```bash
temporal server start-dev
```

**Terminal 2** - Run the worker:

```bash
uv run python -m worker
```

**Terminal 3** - Start execution:

```bash
uv run python -m start_workflow "What's the best restaurant in San Francisco?"
```

## Create the data structures

We will use Python classes to ensure information passes between agents in a
structured way.

The Planning Agent creates a `ResearchPlan`, which includes a research question,
a list of `ResearchAspects`, expected sources, a search strategy, and success
criteria. ResearchAspects include an aspect name, a priority, and a description.

```python
class ResearchPlan(BaseModel):
    research_question: str
    key_aspects: List[ResearchAspect]
    expected_sources: List[str]
    search_strategy: str
    success_criteria: List[str]
```

```python
class ResearchAspect(BaseModel):
    aspect: str
    priority: int
    description: str
```

The Query Generation Agent creates a `QueryPlan`, and generates a list of
`SearchQueries`.

```python
class QueryPlan(BaseModel):
    queries: List[SearchQuery]
```

```python
class SearchQuery(BaseModel):
    query: str
    rationale: str
    expected_info_type: str
    priority: int
```

The Web Search Agent creates a `SearchResult`, which includes a query, a list of
sources, a key finding, a relevance score, and a list of citations.

```python
class SearchResult(BaseModel):
    query: str
    sources: List[str]
    key_findings: str
    relevance_score: float
    citations: List[str]
```

Finally, the Report Synthesis Agent creates a `ResearchReport`, which includes
an executive summary, a detailed analysis, a list of key findings, a confidence
assessment, a list of citations, and a list of follow-up questions.

```python
class ResearchReport(BaseModel):
    executive_summary: str
    detailed_analysis: str
    key_findings: List[str]
    confidence_assessment: str
    citations: List[str]
    follow_up_questions: List[str]
```

## Create the Agents

The deep research system uses four specialized agents, each implemented as
Temporal activities. In this implementation, each agent is implemented as a
single call to the OpenAI Responses API.

This is possible because we are using structured outputs, which guarantee the
response will be in the correct format, eliminating the need for retries.

The web search agent also requires only a single API call because OpenAI
integrates the web search tool into the Responses API.

These agents run in the Workflow and use the `invoke_model` activity to make
OpenAI API calls. It is critical to set the `start_to_close_timeout` for these
activities to a value that is long enough to complete the task. If it is too
short, the activity will fail with a timeout error, causing a retry loop that
never completes. Response times for reasoning models such as `GPT-5` can vary
significantly depending on the nature of the request. Web search times also vary
depending on the size and content of the documents located by the search.

### Research Planning Agent

Analyzes research queries and creates comprehensive research strategies. Takes
an unstructured question and decomposes it into specific research aspects with
priorities, identifies expected source types, and defines success criteria.

*File: agents/research_planning.py*

```python
from .models import ResearchPlan
from .config import COMPLEX_REASONING_MODEL
from activities.invoke_model import invoke_model, InvokeModelRequest
from temporalio import workflow
from datetime import timedelta

RESEARCH_PLANNING_INSTRUCTIONS = """
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
```

### Query Generation Agent

Converts research plans into optimized web search queries. Creates 3-5 diverse
queries that target different information types (factual data, expert analysis,
case studies, recent news) with varied search styles and temporal modifiers.

*File: agents/research_query_generation.py*

```python
from .models import QueryPlan, ResearchPlan
from .config import EFFICIENT_PROCESSING_MODEL
from activities.invoke_model import invoke_model, InvokeModelRequest
from temporalio import workflow
from datetime import timedelta

QUERY_GENERATION_INSTRUCTIONS = """
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
```

### Web Search Agent

Executes searches using OpenAI's web search tool and analyzes results.
Prioritizes authoritative sources, extracts key findings, assesses relevance,
and provides proper citations with reliability assessments.

*File: agents/research_web_search.py*

```python
from .models import SearchResult, SearchQuery
from .config import EFFICIENT_PROCESSING_MODEL
from activities.invoke_model import invoke_model, InvokeModelRequest
from temporalio import workflow
from datetime import timedelta

WEB_SEARCH_INSTRUCTIONS = """
You are a web research specialist who finds and evaluates information from web sources.

CORE RESPONSIBILITIES:
1. Execute web searches using the web search tool
2. Prioritize authoritative sources: academic, government, established research organizations, prominent news outlets, primary sources
3. Extract key information relevant to the research question
4. Provide proper citations and assess reliability

APPROACH:
- Focus on information directly relevant to the research question
- Extract specific facts, data points, and evidence
- Note conflicting information and limitations
- Flag questionable or unverified claims

OUTPUT REQUIREMENTS:
- query: The search query that was executed
- sources: URLs and source descriptions consulted
- key_findings: Synthesized information relevant to research question (2-4 paragraphs)
- relevance_score: 0.0-1.0 assessment of how well results address the query
- citations: Formatted sources with URLs
"""


async def search_web(query: SearchQuery) -> SearchResult:
    search_input = f"""
Search Query: {query.query}
Query Rationale: {query.rationale}
Expected Information Type: {query.expected_info_type}
Priority Level: {query.priority}

Please search for information using the provided query and analyze the results according to the instructions.
"""
    result = await workflow.execute_activity(
        invoke_model,
        InvokeModelRequest(
            model=EFFICIENT_PROCESSING_MODEL,
            instructions=WEB_SEARCH_INSTRUCTIONS,
            input=search_input,
            response_format=SearchResult,
            tools=[{"type": "web_search"}],
        ),
        start_to_close_timeout=timedelta(seconds=300),
        summary="Searching web for information",
    )
    return result.response
```

### Report Synthesis Agent

Directs the agent to synthesize all research findings into comprehensive,
well-cited reports. These should include structured narratives with executive
summaries, detailed analysis, key findings, confidence assessments, and
follow-up research questions.

*File: agents/research_report_synthesis.py*

```python
from typing import List
from temporalio import workflow
from datetime import timedelta
from .models import ResearchReport, ResearchPlan, SearchResult
from .config import COMPLEX_REASONING_MODEL
from activities.invoke_model import invoke_model, InvokeModelRequest

REPORT_SYNTHESIS_INSTRUCTIONS = """
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
            instructions=REPORT_SYNTHESIS_INSTRUCTIONS,
            input=synthesis_input,
            response_format=ResearchReport,
        ),
        start_to_close_timeout=timedelta(seconds=300),
        summary="Generating research report synthesis",
    )

    return result.response
```

## Create the Workflow

The `DeepResearchWorkflow` orchestrates the four-phase research process with
built-in resilience and error handling:

First, planning and query generation agents are run sequentially. Then, the
workflow executes searches concurrently. For robustness, the workflow continues
with partial results if some searches fail. Finally, the report synthesis agent
pulls together the findings into a comprehensive report.

*File: workflows/deep_research_workflow.py*

```python
from temporalio import workflow
from temporalio.exceptions import ApplicationError
import asyncio
from typing import List

from agents.research_planning import plan_research
from agents.research_query_generation import generate_queries
from agents.research_web_search import search_web
from agents.research_report_synthesis import generate_synthesis
from agents.models import SearchResult


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

```
