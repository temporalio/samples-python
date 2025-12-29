"""Deep Research Agent Graph Definition.

This module implements a multi-step research agent that performs iterative
research to produce comprehensive reports. It demonstrates:
- Parallel search execution using LangGraph's Send API
- Result evaluation and iteration
- Long-running research workflows (showcasing Temporal's durability)
- Report synthesis from multiple sources

The research flow:
1. plan_research - Analyze the topic and generate search queries
2. search (parallel) - Execute multiple searches concurrently
3. evaluate_results - Grade search results for relevance
4. decide_next - Either continue researching or synthesize
5. synthesize - Produce final research report

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class SearchQuery(BaseModel):
    """A search query to execute."""

    query: str = Field(description="The search query to execute")
    purpose: str = Field(description="What information this query aims to find")


class ResearchPlan(BaseModel):
    """Research plan with multiple search queries."""

    queries: list[SearchQuery] = Field(
        description="List of search queries to execute", min_length=1, max_length=5
    )


class SearchResult(TypedDict):
    """Result from a single search."""

    query: str
    purpose: str
    results: str
    relevant: bool


class ResearchState(TypedDict):
    """State for the deep research graph.

    Attributes:
        messages: Conversation history with the research question.
        topic: The main research topic extracted from the question.
        search_queries: Planned search queries from the planner.
        search_results: Results from executed searches.
        iteration: Current research iteration (for limiting loops).
        max_iterations: Maximum number of research iterations.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    topic: str
    search_queries: list[SearchQuery]
    search_results: Annotated[list[SearchResult], lambda x, y: x + y]
    iteration: int
    max_iterations: int


class SearchTaskState(TypedDict):
    """State for individual search tasks (used with Send)."""

    query: str
    purpose: str


# Simulated web search results (in production, use a real search API)
MOCK_SEARCH_RESULTS = {
    "langgraph": """LangGraph is a library for building stateful, multi-actor applications
    with LLMs. It provides support for cycles, branches, and state persistence. Key features:
    - StateGraph for defining application flow
    - Built-in persistence and checkpointing
    - Human-in-the-loop support with interrupts
    - Streaming support for real-time updates""",
    "temporal": """Temporal is a durable execution platform. Key concepts:
    - Workflows: Long-running processes that survive failures
    - Activities: Units of work with automatic retries
    - Signals: External events sent to workflows
    - Queries: Read-only state inspection""",
    "durable": """Durable execution ensures code runs to completion despite failures.
    Benefits include: automatic retry of failed operations, state preservation
    across restarts, and reliable execution of long-running processes.""",
    "agent": """AI agents are autonomous systems that use LLMs to decide actions.
    Common patterns include ReAct (reasoning + acting), plan-and-execute,
    and multi-agent collaboration. Tools enable agents to interact with
    external systems and data sources.""",
    "rag": """RAG (Retrieval Augmented Generation) enhances LLM responses with
    external knowledge. Agentic RAG adds decision-making about when to retrieve,
    document grading, and query rewriting for better results.""",
    "research": """Research agents perform multi-step information gathering.
    They plan queries, execute searches, evaluate results, and synthesize
    findings into comprehensive reports.""",
}


def build_deep_research_graph() -> Any:
    """Build a deep research agent graph.

    The graph implements a research workflow that:
    1. Plans research by generating targeted search queries
    2. Executes searches in parallel using Send
    3. Evaluates results for relevance
    4. Iterates if more research is needed
    5. Synthesizes findings into a final report

    Returns:
        A compiled LangGraph that can be executed with ainvoke().
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    def plan_research(state: ResearchState) -> dict[str, Any]:
        """Plan the research by generating search queries.

        Analyzes the research topic and creates a set of targeted
        queries to gather comprehensive information.
        """
        messages = state["messages"]
        topic = next(
            (m.content for m in messages if isinstance(m, HumanMessage)),
            "AI agents",
        )
        topic_str = str(topic)

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
        plan = planner.invoke({"topic": topic_str})

        return {
            "topic": topic_str,
            "search_queries": plan.queries,
            "iteration": state.get("iteration", 0) + 1,
            "max_iterations": state.get("max_iterations", 2),
        }

    def execute_search(state: SearchTaskState) -> dict[str, Any]:
        """Execute a single search query.

        In production, this would call a real search API.
        Here we use mock results for demonstration.
        """
        query = state["query"].lower()
        purpose = state["purpose"]

        # Find matching mock results
        results_parts = []
        for keyword, content in MOCK_SEARCH_RESULTS.items():
            if keyword in query:
                results_parts.append(content)

        if not results_parts:
            results = "No specific results found. The topic may require more specialized research."
        else:
            results = "\n\n".join(results_parts)

        return {
            "search_results": [
                {
                    "query": state["query"],
                    "purpose": purpose,
                    "results": results,
                    "relevant": len(results_parts) > 0,
                }
            ]
        }

    def fan_out_searches(
        state: ResearchState,
    ) -> list[Send]:
        """Fan out to parallel search executions.

        Creates a Send for each search query, enabling parallel execution
        of searches as separate Temporal activities.
        """
        sends = []
        for query in state.get("search_queries", []):
            sends.append(
                Send(
                    "search",
                    {"query": query.query, "purpose": query.purpose},
                )
            )
        return sends

    def evaluate_results(state: ResearchState) -> dict[str, Any]:
        """Evaluate search results for coverage and quality.

        Determines if we have enough relevant information to synthesize
        a comprehensive report, or if more research is needed.
        """
        results = state.get("search_results", [])
        relevant_count = sum(1 for r in results if r.get("relevant", False))

        # Simple evaluation: check if we have enough relevant results
        coverage = relevant_count / max(len(results), 1)

        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Research iteration {state['iteration']}: "
                    f"Found {relevant_count}/{len(results)} relevant results. "
                    f"Coverage: {coverage:.0%}",
                }
            ]
        }

    def should_continue(state: ResearchState) -> Literal["synthesize", "plan"]:
        """Decide whether to continue researching or synthesize.

        Routes to synthesis if:
        - We have reached max iterations
        - We have sufficient relevant results

        Otherwise, continues with another research iteration.
        """
        iteration = state.get("iteration", 1)
        max_iterations = state.get("max_iterations", 2)
        results = state.get("search_results", [])
        relevant_count = sum(1 for r in results if r.get("relevant", False))

        # Continue if under max iterations and low coverage
        if iteration < max_iterations and relevant_count < 2:
            return "plan"

        return "synthesize"

    def synthesize_report(state: ResearchState) -> dict[str, Any]:
        """Synthesize research findings into a comprehensive report.

        Combines all relevant search results into a well-structured
        research report that answers the original question.
        """
        topic = state.get("topic", "the research topic")
        results = state.get("search_results", [])

        # Compile all findings
        findings = []
        for result in results:
            if result.get("relevant", False):
                findings.append(
                    f"### {result['purpose']}\n{result['results']}"
                )

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
        report = chain.invoke({"topic": topic, "findings": findings_text})

        return {"messages": [{"role": "assistant", "content": report}]}

    # Build the research graph
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("plan", plan_research)
    workflow.add_node("search", execute_search)
    workflow.add_node("evaluate", evaluate_results)
    workflow.add_node("synthesize", synthesize_report)

    # Add edges
    workflow.add_edge(START, "plan")

    # Fan out from plan to parallel searches
    workflow.add_conditional_edges("plan", fan_out_searches, ["search"])

    # All searches converge at evaluate
    workflow.add_edge("search", "evaluate")

    # Decide whether to continue or synthesize
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {"synthesize": "synthesize", "plan": "plan"},
    )

    workflow.add_edge("synthesize", END)

    return workflow.compile()
