# Agentic RAG

An intelligent RAG (Retrieval Augmented Generation) agent that decides when to retrieve documents, grades their relevance, and rewrites queries when needed.

## What This Sample Demonstrates

- **`create_agent` pattern**: Uses LangChain's `create_agent` for the retrieval step
- **Document grading**: Retrieved documents are evaluated for relevance before generating answers
- **Query rewriting**: If documents aren't relevant, the query is reformulated and retrieval is retried
- **Durable execution**: Graph nodes run as Temporal activities with automatic retries
- **Crash recovery**: If the worker fails, execution resumes from the last completed node

## How It Works

The graph implements an agentic RAG pattern with `create_agent` for retrieval:

```
                              +-------+
                              | START |
                              +---+---+
                                  |
                                  v
                        +-----------------+
             +--------->| retrieve_agent  |<--------+
             |          | (create_agent)  |         |
             |          +-----------------+         |
             |                  |                   |
             |     "not relevant"   "relevant"      |
             |          |                |          |
         +---+---+      |                |     +----+
         |rewrite|<-----+                +---->| END|
         +-------+                             +----+
                                                 ^
                                                 |
                                           +-----+----+
                                           | generate |
                                           +----------+
```

1. **retrieve_agent**: Uses `create_agent` to decide whether to retrieve and fetch documents (runs as single activity)
2. **grade_documents**: Conditional edge that evaluates document relevance
3. **generate**: Produces the final answer using relevant documents (runs as activity)
4. **rewrite**: Reformulates the query if documents weren't relevant, then retries (runs as activity)

### Subgraph Behavior

The Temporal LangGraph plugin automatically detects subgraphs (like `create_agent`) and executes their **inner nodes as separate activities**. This means:

- The retrieve_agent subgraph's `model` and `tools` nodes run as separate Temporal activities
- Each node has its own retry/timeout configuration
- If the worker crashes during retrieval, execution resumes from the last completed inner node
- You get full durability without manually adding separate nodes

The sample includes a knowledge base with documents about:
- LangGraph features and capabilities
- Temporal concepts (workflows, activities, signals, queries)
- ReAct pattern for AI agents
- Agentic RAG patterns
- Human-in-the-loop workflows

## Prerequisites

- Temporal server running locally (`temporal server start-dev`)
- OpenAI API key set: `export OPENAI_API_KEY=your-key`

## Running the Example

First, start the worker:
```bash
uv run langgraph_plugin/graph_api/agentic_rag/run_worker.py
```

Then, in a separate terminal, run the workflow:
```bash
uv run langgraph_plugin/graph_api/agentic_rag/run_workflow.py
```

## Expected Output

```
The ReAct (Reasoning and Acting) pattern is an approach where an LLM alternates
between thinking about what to do and taking actions. The loop consists of:
1. Think - The LLM reasons about the current state and what action to take
2. Act - Execute the chosen action (e.g., call a tool)
3. Observe - Process the result of the action
4. Repeat until the task is complete

When combined with Temporal, the ReAct pattern gains durability because each
graph node runs as a Temporal activity. This means progress is saved after each
node completes, and if the worker crashes, execution resumes from the last
completed node.
```

## Sample Queries

You can modify the query in `run_workflow.py` to test different scenarios:

- **Retrieval needed**: "What is LangGraph and how does it work?"
- **Multi-topic**: "How do Temporal signals work with human-in-the-loop workflows?"
- **Off-topic (no retrieval)**: "What's 2 + 2?" (agent responds directly)
- **Needs rewriting**: "Tell me about durable stuff" (vague query gets rewritten)

## Architecture Notes

The sample uses an in-memory vector store with sample documents for simplicity. In production, you would:

1. Use a persistent vector store (Pinecone, Weaviate, Chroma, etc.)
2. Load documents from your actual knowledge base
3. Configure appropriate chunk sizes and embedding models

The document grading step adds latency but significantly improves answer quality by ensuring the RAG system only uses relevant context.
