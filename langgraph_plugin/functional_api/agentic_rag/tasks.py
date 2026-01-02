"""Task definitions for the Agentic RAG system.

Each @task runs as a Temporal activity with automatic retries.
Demonstrates intelligent document retrieval with grading and query rewriting.
"""

import os
from typing import Any, Literal

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.func import task
from pydantic import BaseModel, Field

# Sample documents about AI agents and LangGraph for the knowledge base
SAMPLE_DOCUMENTS = [
    Document(
        page_content="""LangGraph is a library for building stateful, multi-actor applications with LLMs.
        It extends LangChain with the ability to coordinate multiple chains across
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
        - Queries: Read-only operations to inspect workflow state""",
        metadata={"source": "temporal_overview", "topic": "temporal"},
    ),
    Document(
        page_content="""The ReAct (Reasoning and Acting) pattern is an approach where an LLM
        alternates between thinking about what to do and taking actions. The loop is:
        1. Think: The LLM reasons about the current state and what action to take
        2. Act: Execute the chosen action (e.g., call a tool)
        3. Observe: Process the result of the action
        4. Repeat until the task is complete""",
        metadata={"source": "react_pattern", "topic": "agents"},
    ),
    Document(
        page_content="""Agentic RAG is an advanced pattern where an AI agent decides when and how
        to retrieve information. Unlike basic RAG which always retrieves, agentic RAG can:
        - Decide if retrieval is needed based on the query
        - Grade retrieved documents for relevance
        - Rewrite queries if initial retrieval fails
        - Combine multiple retrieval strategies""",
        metadata={"source": "agentic_rag_overview", "topic": "rag"},
    ),
]


class DocumentGrade(BaseModel):
    """Grade for document relevance."""

    binary_score: Literal["yes", "no"] = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )


def _create_retriever() -> Any:
    """Create a retriever with sample documents."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = InMemoryVectorStore(embeddings)
    vectorstore.add_documents(SAMPLE_DOCUMENTS)
    return vectorstore.as_retriever(search_kwargs={"k": 2})


@task
async def retrieve_documents(query: str) -> list[dict[str, Any]]:
    """Retrieve relevant documents from the knowledge base.

    Args:
        query: The search query.

    Returns:
        List of retrieved documents with content and metadata.
    """
    retriever = _create_retriever()
    docs = await retriever.ainvoke(query)

    return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]


@task
async def grade_documents(
    question: str, documents: list[dict[str, Any]]
) -> dict[str, Any]:
    """Grade retrieved documents for relevance.

    Args:
        question: The user's question.
        documents: Retrieved documents to grade.

    Returns:
        Dict with relevance flag and graded documents.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )

    if not documents:
        return {"relevant": False, "documents": []}

    # Combine document content for grading
    docs_content = "\n\n".join(d["content"] for d in documents)

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

    grader = grade_prompt | model.with_structured_output(DocumentGrade)
    result: Any = await grader.ainvoke(
        {"documents": docs_content, "question": question}
    )

    return {
        "relevant": result.binary_score == "yes",
        "documents": documents,
    }


@task
async def rewrite_query(original_query: str) -> str:
    """Rewrite the query to improve retrieval.

    Args:
        original_query: The original question.

    Returns:
        An improved query.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
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
    improved = await chain.ainvoke({"question": original_query})

    return improved


@task
async def generate_answer(question: str, documents: list[dict[str, Any]]) -> str:
    """Generate an answer using the retrieved documents.

    Args:
        question: The user's question.
        documents: Relevant documents to use for answering.

    Returns:
        The generated answer.
    """
    model = ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3,
    )

    docs_content = "\n\n".join(d["content"] for d in documents)

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
    answer = await chain.ainvoke({"context": docs_content, "question": question})

    return answer
