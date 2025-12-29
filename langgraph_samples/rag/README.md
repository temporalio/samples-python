# RAG (Retrieval Augmented Generation) Samples

This directory contains samples demonstrating RAG patterns with Temporal LangGraph integration.

## Available Samples

### [Agentic RAG](./agentic_rag/README.md)

An intelligent RAG system that decides when to retrieve documents, grades their relevance, and can rewrite queries when initial retrieval fails.

**Key Features:**
- Agent-driven retrieval decisions
- Document relevance grading
- Query rewriting for better retrieval
- Durable execution with Temporal

### [Deep Research Agent](./deep_research/README.md)

A multi-step research agent that performs iterative research to produce comprehensive reports.

**Key Features:**
- Research planning with targeted search queries
- Parallel search execution using LangGraph's Send API
- Result evaluation and iteration
- Long-running research with Temporal durability
- Report synthesis from multiple sources

## Prerequisites

- Temporal server [running locally](https://docs.temporal.io/cli/server#start-dev)
- OpenAI API key set: `export OPENAI_API_KEY=your-key`
- Dependencies installed via `uv sync --group langgraph`
