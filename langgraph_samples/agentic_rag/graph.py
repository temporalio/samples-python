"""Agentic RAG Graph Definition.

This module implements an agentic RAG (Retrieval Augmented Generation) system
that intelligently decides when to retrieve documents, grades their relevance,
and can rewrite queries when documents aren't helpful.

The graph uses create_agent for the retrieval step, which provides a convenient
way to build a ReAct-style agent. The outer graph adds document grading and
query rewriting logic.

Flow:
1. retrieve_agent - Uses create_agent to decide and fetch documents
2. grade_documents - Evaluates document relevance (conditional routing)
3. generate - Produces final answer using relevant documents
4. rewrite - Reformulates query if documents aren't relevant, then retries

Architecture Note:
The Temporal LangGraph plugin automatically detects subgraphs (like create_agent)
and executes their inner nodes as separate activities. This means:
- The retrieve_agent subgraph's 'model' and 'tools' nodes run as separate activities
- Each tool call has its own retry/timeout configuration
- If the worker crashes, execution resumes from the last completed inner node
- The generate, rewrite nodes in the outer graph also run as separate activities

Note: This module is only imported by the worker (not by the workflow).
LangGraph cannot be imported in the workflow sandbox.
"""

import os
from typing import Annotated, Any, Literal, Sequence, cast

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langchain.agents import create_agent

# Sample documents about AI agents and LangGraph for the knowledge base
SAMPLE_DOCUMENTS = [
    Document(
        page_content="""LangGraph is a library for building stateful, multi-actor applications with LLMs.
        It extends LangChain with the ability to coordinate multiple chains (or actors) across
        multiple steps of computation in a cyclic manner. Key features include:
        - Support for cycles and branching in agent workflows
        - Built-in persistence for pausing and resuming
        - Human-in-the-loop support with interrupts
        - Streaming support for real-time updates""",
        metadata={"source": "langgraph_overview", "topic": "langgraph"},
    ),
    Document(
        page_content="""Temporal is a durable execution platform that enables developers to build
        applications that are reliable by default. Key concepts include:
        - Workflows: Long-running, reliable processes that survive failures
        - Activities: Individual units of work that can be retried
        - Signals: External events that can be sent to running workflows
        - Queries: Read-only operations to inspect workflow state
        The Temporal LangGraph integration runs each graph node as a Temporal activity.""",
        metadata={"source": "temporal_overview", "topic": "temporal"},
    ),
    Document(
        page_content="""The ReAct (Reasoning and Acting) pattern is an approach where an LLM
        alternates between thinking about what to do and taking actions. The loop is:
        1. Think: The LLM reasons about the current state and what action to take
        2. Act: Execute the chosen action (e.g., call a tool)
        3. Observe: Process the result of the action
        4. Repeat until the task is complete
        This pattern allows LLMs to effectively use tools and handle multi-step tasks.""",
        metadata={"source": "react_pattern", "topic": "agents"},
    ),
    Document(
        page_content="""Agentic RAG (Retrieval Augmented Generation) is an advanced pattern where
        an AI agent decides when and how to retrieve information. Unlike basic RAG which always
        retrieves, agentic RAG can:
        - Decide if retrieval is needed based on the query
        - Grade retrieved documents for relevance
        - Rewrite queries if initial retrieval fails
        - Combine multiple retrieval strategies
        This leads to more efficient and accurate responses.""",
        metadata={"source": "agentic_rag_overview", "topic": "rag"},
    ),
    Document(
        page_content="""Human-in-the-loop workflows allow AI systems to pause and wait for
        human input at critical decision points. In LangGraph, this is implemented using
        the interrupt() function. When combined with Temporal:
        - The workflow pauses durably while waiting for human input
        - Temporal signals are used to receive the human response
        - The workflow resumes exactly where it left off
        This enables approval workflows, human review of AI outputs, and collaborative AI.""",
        metadata={"source": "hitl_overview", "topic": "human_in_loop"},
    ),
]


class AgentState(TypedDict):
    """State schema for the agentic RAG graph.

    Attributes:
        messages: Conversation history with add_messages reducer for merging.
        docs_relevant: Whether retrieved documents are relevant (set by grade_documents).
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    docs_relevant: bool


class DocumentGrade(BaseModel):
    """Grade for document relevance."""

    binary_score: Literal["yes", "no"] = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )


def _create_retriever() -> Any:
    """Create a retriever with sample documents.

    Returns:
        A retriever that can search the sample knowledge base.
    """
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = InMemoryVectorStore(embeddings)
    vectorstore.add_documents(SAMPLE_DOCUMENTS)
    return vectorstore.as_retriever(search_kwargs={"k": 2})


def build_agentic_rag_graph() -> Any:
    """Build an agentic RAG graph with document grading.

    Uses create_agent for the retrieval step. The outer graph adds document
    grading and query rewriting logic around the retrieval agent.

    Flow:
    1. retrieve_agent decides whether to retrieve and fetches docs
    2. grade_documents checks relevance (conditional edge)
    3. generate produces answer OR rewrite reformulates query

    Returns:
        A compiled LangGraph that can be executed with ainvoke().
    """
    # Create the model
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    # Create retriever and tool
    retriever = _create_retriever()
    retriever_tool = create_retriever_tool(
        retriever,
        "retrieve_knowledge",
        "Search the knowledge base for information about LangGraph, Temporal, "
        "AI agents, RAG patterns, and human-in-the-loop workflows. "
        "Use this when the user asks about these topics.",
    )
    tools = [retriever_tool]

    # Build retrieval agent using create_agent
    # Note: create_agent returns a compiled graph. The Temporal plugin automatically
    # detects this subgraph and runs its inner nodes (model, tools) as separate activities.
    retrieve_agent: Any = create_agent(model, tools)

    # Grade documents for relevance (as a node/activity, not conditional edge)
    def grade_documents(state: AgentState) -> dict[str, Any]:
        """Grade retrieved documents for relevance.

        This is a node (activity) that examines the retrieved documents and
        determines if they contain information relevant to answering the
        user's question. The result is stored in state for routing.

        Note: This must be a node (not conditional edge) because it makes
        an LLM call. LLM calls should run as Temporal activities for proper
        durability and retry handling.
        """
        # Set up structured output for grading
        grader = model.with_structured_output(DocumentGrade)

        # Get the question (first human message) and docs (last message with tool results)
        messages = state["messages"]
        question = next(
            (m.content for m in messages if isinstance(m, HumanMessage)), ""
        )

        # Find the retrieved documents in the messages
        docs_content = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, str):
                # Tool messages contain the retrieved documents
                if hasattr(msg, "tool_call_id"):
                    docs_content = msg.content
                    break

        if not docs_content:
            return {"docs_relevant": False}

        # Grade the documents
        grade_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a grader assessing relevance of retrieved documents to a user question.\n"
                    "If the documents contain information related to the question, grade as relevant.\n"
                    "Give a binary score 'yes' or 'no' to indicate relevance.",
                ),
                (
                    "human",
                    "Retrieved documents:\n{documents}\n\nUser question: {question}",
                ),
            ]
        )

        chain = grade_prompt | grader
        result = cast(
            DocumentGrade,
            chain.invoke({"documents": docs_content, "question": question}),
        )

        return {"docs_relevant": result.binary_score == "yes"}

    # Simple routing function (no LLM call - safe for workflow context)
    def route_after_grading(state: AgentState) -> Literal["generate", "rewrite"]:
        """Route based on document relevance grade.

        This is a pure function that just checks the grade result.
        Safe to run in workflow context since it makes no external calls.
        """
        return "generate" if state.get("docs_relevant", False) else "rewrite"

    # Generate answer using retrieved documents
    def generate(state: AgentState) -> dict[str, Any]:
        """Generate answer using the retrieved documents.

        Takes the relevant documents and user question to produce
        a well-grounded response.
        """
        messages = state["messages"]
        question = next(
            (m.content for m in messages if isinstance(m, HumanMessage)), ""
        )

        # Find the retrieved documents
        docs_content = ""
        for msg in reversed(messages):
            if hasattr(msg, "tool_call_id") and hasattr(msg, "content"):
                content = msg.content
                docs_content = content if isinstance(content, str) else str(content)
                break

        # Generate response using RAG prompt
        rag_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an assistant answering questions using the provided context.\n"
                    "Use the following retrieved documents to answer the question.\n"
                    "If the documents don't contain enough information, say so.\n"
                    "Keep your answer concise and well-structured.",
                ),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ]
        )

        chain = rag_prompt | model | StrOutputParser()
        response = chain.invoke({"context": docs_content, "question": question})

        return {"messages": [{"role": "assistant", "content": response}]}

    # Rewrite query for better retrieval
    def rewrite(state: AgentState) -> dict[str, Any]:
        """Rewrite the query to improve retrieval.

        Analyzes the original question and formulates an improved version
        that may yield more relevant documents.
        """
        messages = state["messages"]
        question = next(
            (m.content for m in messages if isinstance(m, HumanMessage)), ""
        )

        rewrite_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a question rewriter. Look at the input question and try to reason "
                    "about the underlying intent. Reformulate the question to be more specific "
                    "and likely to retrieve relevant documents about LangGraph, Temporal, AI agents, "
                    "or related topics.",
                ),
                (
                    "human",
                    "Original question: {question}\n\nFormulate an improved question:",
                ),
            ]
        )

        chain = rewrite_prompt | model | StrOutputParser()
        improved_question = chain.invoke({"question": question})

        return {"messages": [HumanMessage(content=improved_question)]}

    # Build the outer graph with grading logic
    workflow = StateGraph(AgentState)

    # Add nodes
    # retrieve_agent is a compiled graph from create_agent - inner nodes run as separate activities
    workflow.add_node("retrieve_agent", retrieve_agent)
    workflow.add_node("grade_documents", grade_documents)  # LLM grading as activity
    workflow.add_node("generate", generate)
    workflow.add_node("rewrite", rewrite)

    # Add edges
    workflow.add_edge(START, "retrieve_agent")

    # After retrieval, grade documents (as activity)
    workflow.add_edge("retrieve_agent", "grade_documents")

    # Route based on grade result (pure function, no LLM call)
    workflow.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {"generate": "generate", "rewrite": "rewrite"},
    )

    # Generate produces final answer
    workflow.add_edge("generate", END)

    # Rewrite goes back to retrieve_agent to try again
    workflow.add_edge("rewrite", "retrieve_agent")

    return workflow.compile()
